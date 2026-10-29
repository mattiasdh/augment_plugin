#!/usr/bin/env python3
"""The facts behind the morning briefing (skills/brief), as JSON. Reads, never writes.

What happened in the vault over a window, read from git and the vault's own files, so
the model writing the briefing judges and phrases but never has to dig:

- every commit by kind (the person's own edits in Obsidian or on mobile, and the system's
  CAPTURE, WRITE, COMMENT, MEMORY, DREAM, VERIFY, PROCESS, MINT, RECORD commits);
- the notes the person changed, grouped by project or context as the sources view groups
  them, each with the lines they added (frontmatter left out), the checkboxes added or
  ticked, and the added lines that read like an action (an owner alias from config, or an
  action word in NL, FR or EN) flagged as candidates;
- captures, comments and corrections written into the source layer by Claude;
- memory cards added, updated or superseded, and skill memories rewritten;
- the nightly runs in the window, and the items in the review queue awaiting the person;
- session records written in the window, and every record not yet closed.

The window runs from yesterday 00:00 to now, so a briefing always covers the whole of
the day before even when one was already written during it; when the previous briefing
(`window_until:` in augment_wiki/view/briefing.md) ended earlier than that, within seven
days, the window reaches back to it so missed days are not lost. Times are read in `briefing.timezone` (UTC unless config.yaml names one). `--date D` reads one calendar day.

    gen_briefing.py <vault> [--date YYYY-MM-DD | --since ISO --until ISO]

Notes declared `#excluded` never appear, and folders listed in `briefing.skip` are left
out (`notes/_assets` and `notes/_pdf` by default). Everything else under the source root
counts, out-of-scope folders included: the briefing is the person's own view of their
day, not a compilation, so the to-do folders scope rules ignore are exactly what it needs.
"""
import _cli
import argparse, datetime, json, os, re, subprocess, sys
from collections import defaultdict
_cli.help_guard()

import _memory as M
from _gen_util import context_of, load_config, skills_root, split_note
import record_write as R

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbe4904"
VIEW = "augment_wiki/view/briefing.md"          # the index: today's briefing, then every earlier one
DATED = "augment_wiki/view/briefings"           # one file per morning, briefing-YYYYMMDD.md
QUEUE = "augment_wiki/verify-queue.md"
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def dated(root):
    """Every dated briefing, newest first, as vault-relative paths."""
    d = os.path.join(root, DATED)
    if not os.path.isdir(d):
        return []
    names = [f for f in os.listdir(d) if re.fullmatch(r"briefing-\d{8}\.md", f)]
    return [f"{DATED}/{f}" for f in sorted(names, reverse=True)]


def dated_path(day):
    return f"{DATED}/briefing-{day:%Y%m%d}.md"
SYSTEM = re.compile(r"^(CAPTURE|WRITE|COMMENT|CORRECTION|MEMORY|DREAM|VERIFY|PROCESS|MINT|RECORD|USAGE|BRIEF|"
                    r"VERIFY\+PROCESS|[A-Z][A-Z+]{2,})\b[: ]")
ACTION_WORDS = [
    # EN
    "todo", "to do", "action", "follow up", "check", "send", "ask", "deadline", "asap", "confirm",
    # NL
    "te doen", "actie", "opvolgen", "navragen", "nakijken", "bezorgen", "doorsturen", "sturen", "bellen",
    "nagaan", "bevestigen", "tegen ", "voor vrijdag", "deadline",
    # FR
    "à faire", "a faire", "à prévoir", "a prevoir", "à confirmer", "a confirmer", "à vérifier", "a verifier",
    "vérifier", "envoyer", "rappeler", "relancer", "demander", "transmettre", "pour le ",
]
TASK = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\[( |x|X|/|-)\]\s+(.*)$")
DONE = re.compile(r"(\b(done|ok|fait|gedaan|klaar|réglé|afgehandeld)\b|✓|✔)\W*$", re.I)
BULK = 300            # added lines past which a note is an import, not writing
PER_NOTE = 40          # added lines shown per note; candidates are always kept
TOTAL = 400            # added lines shown across the briefing


def git(root, *args):
    r = subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=root, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def tzinfo(cfg):
    name = str((cfg.get("briefing") or {}).get("timezone") or "UTC")
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name), name
    except Exception:
        return datetime.timezone.utc, "UTC"


def window(root, cfg, a):
    tz, tzname = tzinfo(cfg)
    now = datetime.datetime.now(tz).replace(second=0, microsecond=0)
    if a.date:
        d = datetime.datetime.strptime(a.date, "%Y-%m-%d").replace(tzinfo=tz)
        return d, d + datetime.timedelta(days=1), tzname, "date"
    if a.since:
        s = datetime.datetime.fromisoformat(a.since)
        u = datetime.datetime.fromisoformat(a.until) if a.until else now
        return (s if s.tzinfo else s.replace(tzinfo=tz)), (u if u.tzinfo else u.replace(tzinfo=tz)), tzname, "given"
    y = (now - datetime.timedelta(days=1)).replace(hour=0, minute=0)
    last = (dated(root) or [VIEW])[0]
    fm, _ = split_note(open(os.path.join(root, last), encoding="utf-8").read()) if os.path.exists(os.path.join(root, last)) else ({}, "")
    prev = fm.get("window_until")
    if prev:
        try:
            p = datetime.datetime.fromisoformat(str(prev))
            p = p if p.tzinfo else p.replace(tzinfo=tz)
            if now - datetime.timedelta(days=7) <= p < y:
                return p, now, tzname, "since the previous briefing, more than a day ago"
        except ValueError:
            pass
    return y, now, tzname, "since yesterday 00:00"


def commits(root, since, until):
    out, cur = [], None
    raw = git(root, "log", f"--since={since.isoformat()}", f"--until={until.isoformat()}", "--no-renames",
              "--name-status", "--pretty=@@%H\t%aI\t%s")
    for ln in raw.splitlines():
        if ln.startswith("@@"):
            sha, at, subj = ln[2:].split("\t", 2)
            m = SYSTEM.match(subj)
            kind = "merge" if subj.startswith("Merge ") else (m.group(1) if m else "person")
            cur = {"sha": sha[:7], "at": at, "kind": kind, "subject": subj, "files": []}
            out.append(cur)
        elif ln.strip() and cur is not None and "\t" in ln:
            st, path = ln.split("\t", 1)
            cur["files"].append((st[0], path))
    return list(reversed(out))      # oldest first


def frontmatter_end(text):
    """The number of leading lines that are frontmatter (0 when none)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return 0
    for i, l in enumerate(lines[1:], 2):
        if l.strip() == "---":
            return i
    return 0


def diff_lines(root, base, tip, path):
    """(added [(line_no, text)], removed [text]) of one file between two commits, -U0."""
    added, removed, n = [], [], 0
    for ln in git(root, "diff", "-U0", "--no-color", "--no-renames", base, tip, "--", path).splitlines():
        if ln.startswith("@@"):
            m = re.search(r"\+(\d+)", ln)
            n = int(m.group(1)) if m else 0
        elif ln.startswith("+++") or ln.startswith("---"):
            continue
        elif ln.startswith("+"):
            added.append((n, ln[1:]))
            n += 1
        elif ln.startswith("-"):
            removed.append(ln[1:])
    return added, removed


def norm_task(t):
    return re.sub(r"\s+", " ", re.sub(r"[⏫🔼🔽📅⏳🛫✅➕🔁].*$", "", t)).strip().lower()


def marker_rx(cfg):
    b = cfg.get("briefing") or {}
    aliases = [str(x) for x in (b.get("owner_aliases") or [cfg.get("author") or ""]) if str(x).strip()]
    words = [str(x) for x in (b.get("action_words") or ACTION_WORDS)]
    alias = r"(?<![\w])(" + "|".join(re.escape(x) for x in aliases) + r")(?![\w])" if aliases else r"(?!x)x"
    word = r"(?<![\w])(" + "|".join(re.escape(w.strip()) for w in words if w.strip()) + r")"
    return re.compile(alias, re.I), re.compile(word, re.I), re.compile(r"(→|->|=>|\?\s*$)")


def _new(root, base, p):
    return subprocess.run(["git", "cat-file", "-e", f"{base}:{p}"], cwd=root, capture_output=True).returncode != 0


def note_changes(root, cfg, base, tip, paths, rx):
    alias_rx, word_rx, arrow_rx = rx
    out = []
    for p in sorted(paths):
        try:
            text = subprocess.run(["git", "show", f"{tip}:{p}"], cwd=root, capture_output=True).stdout.decode("utf-8", "replace")
        except Exception:
            text = ""
        if not text:
            continue                                       # deleted in the window
        fm, _ = split_note(text)
        if "#excluded" in str(fm.get("augment", "")):
            continue
        fe = frontmatter_end(text)
        added, removed = diff_lines(root, base, tip, p)
        added = [(n, t) for n, t in added if n > fe and t.strip() and t.strip() != "---"]
        if not added:
            continue
        if len(added) > BULK:
            # An import (a converted PDF, a pasted table), not a day's writing: listed, never mined.
            out.append({"path": p, "status": "added" if _new(root, base, p) else "changed", "added_lines": len(added),
                        "bulk": True, "tasks_new": [], "tasks_done": [], "action_candidates": [], "lines": []})
            continue
        gone = {norm_task(m.group(2)) for t in removed for m in [TASK.match(t)] if m and m.group(1) == " "}
        tasks_new, tasks_done, cands, lines = [], [], [], []
        for n, t in added:
            m = TASK.match(t)
            if m:
                if m.group(1) == " ":
                    tasks_new.append({"line": n, "text": m.group(2).strip()})
                elif m.group(1) in "xX":
                    tasks_done.append({"line": n, "text": m.group(2).strip(), "was_open": norm_task(m.group(2)) in gone})
                continue
            why = [k for k, r in (("owner", alias_rx), ("action", word_rx), ("arrow", arrow_rx), ("done", DONE)) if r.search(t)]
            row = {"line": n, "text": t.strip()[:300]}
            if why:
                cands.append(dict(row, marker=why))
            lines.append(row)
        new = _new(root, base, p)
        out.append({"path": p, "status": "added" if new else "changed", "added_lines": len(added), "tasks_new": tasks_new,
                    "tasks_done": tasks_done, "action_candidates": cands, "lines": lines})
    return out


def memory_changes(root, cs):
    cards = {slug: fm for slug, fm, _ in M.load_cards(root)}
    paths = M.card_files(root)
    out, seen = [], 0
    for c in cs:
        if c["kind"] != "MEMORY":
            continue
        m = re.match(r"MEMORY:\s+(\w+)\s+(?:skill\s+)?(\S+)", c["subject"])
        if not m:
            continue
        act, slug = m.groups()
        if act == "seen":
            seen += 1
            continue
        fm = cards.get(slug, {})
        path = paths.get(slug)
        out.append({"action": act, "slug": slug, "title": fm.get("title", ""), "summary": fm.get("summary", ""),
                    "skill": "skill " in c["subject"], "at": c["at"], "link": M.card_rel(path, root) if path else None})
    return out, seen


def dream_runs(root, since, until):
    out = []
    p = os.path.join(root, "augment_wiki/history.jsonl")
    if not os.path.exists(p):
        return out
    lo, hi = since.date().isoformat(), until.date().isoformat()
    for ln in open(p, encoding="utf-8"):
        if '_run"' not in ln:
            continue
        try:
            e = json.loads(ln)
        except ValueError:
            continue
        if str(e.get("kind", "")).endswith("_run") and lo <= str(e.get("ran", ""))[:10] <= hi:
            out.append({"id": e.get("id"), "kind": e.get("kind"), "ran": e.get("ran"), "phases": e.get("phases", {})})
    return out


def queue_items(root):
    p = os.path.join(root, "augment_wiki/verify-queue.md")
    if not os.path.exists(p):
        return []
    text = open(p, encoding="utf-8").read()
    sec = re.split(r"^## Queued for confirmation[ \t]*$", text, maxsplit=1, flags=re.M)
    if len(sec) < 2:
        return []
    body = re.split(r"\n## ", sec[1], maxsplit=1)[0]
    out = []
    for ln in body.splitlines():
        m = re.match(r"^- (Q-\d{4}-\d+)\s*\|\s*(.*)$", ln)
        if m:
            parts = [x.strip() for x in m.group(2).split("|")]
            out.append({"id": m.group(1), "item": parts[0][:400], "ask": (parts[-1] if len(parts) > 1 else "")[:300],
                        "link": f"{QUEUE}#Queued for confirmation"})
    return out


def sessions(root, cfg, since, tz):
    stale_days = int((cfg.get("sessions") or {}).get("stale_days", 14))
    recs = R.load(root)
    lo = since.strftime("%Y-%m-%d %H:%M")
    today = datetime.datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    cutoff = (datetime.datetime.now(tz) - datetime.timedelta(days=stale_days)).strftime("%Y-%m-%d %H:%M")

    def row(rid, fm, body):
        nxt = body.split("## Next steps", 1)[-1].split("\n## ", 1)[0].strip() if "## Next steps" in body else ""
        return {"id": rid, "link": f"{R.DIR}/{rid}.md", "title": fm.get("title"), "status": fm.get("status"), "project": fm.get("project"),
                "updated": str(fm.get("updated", "")), "records": fm.get("records"), "surface": fm.get("surface"),
                "next_steps": nxt[:800], "stale": str(fm.get("updated", "")) < cutoff}
    return {
        "written_in_window": [row(*r) for r in recs if lo <= str(r[1].get("updated", "")) <= today],
        "not_closed": [row(*r) for r in recs if r[1].get("status") != "closed"],
        "stale_days": stale_days,
    }


def project_entities(root, cfg):
    """{folder prefix: wiki entity path} for project folders, read from the index: the
    project entity most of the folder's indexed sources produced."""
    idx = os.path.join(root, "augment_wiki/index.jsonl")
    if not os.path.exists(idx):
        return {}
    entries = [json.loads(l) for l in open(idx, encoding="utf-8") if l.strip()]
    projects = {e["id"] for e in entries if e.get("type") == "entity" and e.get("kind") == "project"}
    rules = [r for r in (cfg.get("source_contexts") or []) if r.get("group_by") == "child"]
    votes = defaultdict(lambda: defaultdict(int))
    for e in entries:
        sid = str(e.get("id", ""))
        for r in rules:
            base = str(r.get("path", "")).rstrip("/") + "/"
            rest = sid[len(base):].split("/") if sid.startswith(base) else []
            if len(rest) > 1:
                for w in e.get("produced") or []:
                    if w in projects:
                        votes[base + rest[0] + "/"][w] += 1
    return {k: max(v, key=v.get) for k, v in votes.items()}


def entity_for(path, ents):
    for pre, ent in ents.items():
        if path.startswith(pre):
            return ent
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("vault")
    ap.add_argument("--date")
    ap.add_argument("--since")
    ap.add_argument("--until")
    ap.add_argument("--scheduled", action="store_true",
                    help="the nightly run: print SKIP and stop on a day briefing.days does not list")
    a = ap.parse_args()
    root = os.path.abspath(a.vault)
    if not os.path.isfile(os.path.join(root, M.MARKER)):
        print(f"REFUSED: {root} is not a vault (no {M.MARKER})")
        sys.exit(1)
    cfg = load_config(root)
    b = cfg.get("briefing") or {}
    tz0, _ = tzinfo(cfg)
    now = datetime.datetime.now(tz0)
    if a.scheduled:
        if b.get("enabled") is False:
            print("SKIP: briefing.enabled is false in config.yaml")
            return
        days = [str(d).strip().lower()[:3] for d in (b.get("days") or DAYS[:5])]
        today = DAYS[now.weekday()]
        if today not in days:
            print(f"SKIP: {today} is not a briefing day (briefing.days: {', '.join(days)}); a briefing asked for by hand still runs")
            return
    since, until, tzname, how = window(root, cfg, a)
    tz = since.tzinfo
    src = str(cfg.get("source_root") or "").strip("/")
    skip = [str(x).strip("/") for x in ((cfg.get("briefing") or {}).get("skip") or [f"{src}/_assets", f"{src}/_pdf"])]
    sr = skills_root(root, cfg) or ""

    cs = [c for c in commits(root, since, until) if c["kind"] != "merge"]
    base = git(root, "rev-list", "-1", f"--before={since.isoformat()}", "HEAD").strip() or EMPTY_TREE
    tip = git(root, "rev-list", "-1", f"--before={until.isoformat()}", "HEAD").strip() or "HEAD"

    def is_note(p):
        return p.endswith(".md") and (not src or p.startswith(src + "/")) and not any(p == s or p.startswith(s + "/") for s in skip) \
            and not (sr and p.startswith(sr + "/"))

    person = {p for c in cs if c["kind"] == "person" for st, p in c["files"] if st != "D" and is_note(p)}
    notes = note_changes(root, cfg, base, tip, person, marker_rx(cfg))

    # Trim the lines shown to the budget, keeping every candidate and task.
    budget = TOTAL
    for n in notes:
        keep = n["lines"][:PER_NOTE] if budget > 0 else []
        n["lines_shown"] = len(keep)
        n["lines"] = keep
        budget -= len(keep)

    ents = project_entities(root, cfg)
    groups = defaultdict(list)
    rules = cfg.get("source_contexts") or []
    for n in notes:
        groups[context_of(n["path"], rules, cfg)].append(n)

    system_writes = [{"kind": c["kind"], "subject": c["subject"], "at": c["at"],
                      "paths": [p for st, p in c["files"] if is_note(p) or p.startswith(f"{src}/_inbox/")]}
                     for c in cs if c["kind"] in ("CAPTURE", "WRITE", "COMMENT", "CORRECTION")]
    mem, seen = memory_changes(root, cs)
    usage = [0, 0]
    for c in cs:
        m = re.match(r"USAGE: (\d+) opens?, (\d+)", c["subject"])
        if m:
            usage[0] += int(m.group(1)); usage[1] += int(m.group(2))
    kinds = defaultdict(int)
    for c in cs:
        kinds[c["kind"]] += 1

    morning = (until - datetime.timedelta(minutes=1)).date() + datetime.timedelta(days=1) if (a.date or a.since) else now.date()
    target = dated_path(morning)
    earlier = [p for p in dated(root) if p != target]
    out = {
        "write_to": target,
        "heading_date": f"{morning:%A} {morning.day} {morning:%B %Y}",
        "previous_briefing": earlier[0] if earlier else None,
        "index": VIEW,
        "queue_link": QUEUE,
        "window": {"since": since.isoformat(), "until": until.isoformat(), "timezone": tzname, "how": how,
                   "base": base[:7], "tip": tip[:7]},
        "commits_by_kind": dict(sorted(kinds.items())),
        "projects": [{"context": k, "entity": next((e for e in (entity_for(n["path"], ents) for n in v) if e), None), "notes": v} for k, v in sorted(groups.items(), key=lambda kv: -sum(n["added_lines"] for n in kv[1]))],
        "source_writes_by_claude": system_writes,
        "memory": {"changed": mem, "confirmed_seen": seen},
        "skill_memories": sorted({p for c in cs for st, p in c["files"] if sr and p.startswith(sr + "/") and p.endswith("/MEMORY.md")}),
        "nightly_runs": dream_runs(root, since, until),
        "queue_awaiting_person": queue_items(root),
        "sessions": sessions(root, cfg, since, tz),
        "usage": {"opens": usage[0], "citations_or_cards_applied": usage[1]},
        "commits": [{k: c[k] for k in ("sha", "at", "kind", "subject")} for c in cs if c["kind"] != "USAGE"],
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
