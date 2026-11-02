#!/usr/bin/env python3
"""Prep facts for upcoming meetings, for the morning briefing's calendar sections (skills/brief).

Reads a small JSON list of calendar events the brief skill wrote to scratch, and for each
event finds the project it belongs to and what to bring to it. Reads, never writes.

Matching, title first:
  1. the event's subject (and location) against each project folder's number and name and
     its wiki note's title and aliases (`project_names` in gen_briefing.py);
  2. only when the title names no project, the attendees' email domains against the domains
     declared in `briefing.project_domains` ({"235 Sapinette": [client.be]}), then those
     found in each project's own notes (the person's own domains, `briefing.own_domains`,
     and public mail providers left out). Domains are used for matching and never output.

For a matched project:
  - `meetings`: its last `briefing.prep_meetings` (3) meeting notes dated before the event,
    by the date in the file name (2026-10-27 …, 2025_01_07 …, 220_240507_ …);
  - `decisions`: the project note's `## Decisions` lines dated on or after the oldest of them;
  - `open`: unticked checkboxes and action-marked lines from those notes, merged across
    meetings: an item that recurs carries `open_since`, one a later note marks done or ticks
    is dropped, and `mine` is set when it names an owner alias;
  - `discuss`: lines marked for discussion (à discuter, te bespreken, to discuss, …) and
    open questions;
  - `agenda_url`: a claude.ai/new link that asks a fresh conversation to draft the agenda
    from those notes, naming them by path and quoting nothing from them.

    meeting_prep.py <vault> --events FILE
    FILE: [{"subject", "start", "end", "location", "all_day", "organiser_is_me",
            "attendee_domains": ["client.be", ...]}]
"""
import _cli
import argparse, datetime, json, os, re, sys, urllib.parse
from collections import defaultdict
_cli.help_guard()

import _memory as M
from _gen_util import load_config, split_note
import gen_briefing as G

PUBLIC = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "hotmail.be", "live.com", "live.be",
          "yahoo.com", "yahoo.fr", "icloud.com", "me.com", "telenet.be", "skynet.be", "proximus.be",
          "scarlet.be", "voo.be", "fastmail.com", "protonmail.com", "proton.me"}
DISCUSS = re.compile(r"(à discuter|a discuter|à aborder|à voir|point ouvert|te bespreken|bespreken|"
                     r"agendapunt|to discuss|for discussion|\?\s*$)", re.I)
DATE_RE = [re.compile(r"^(20\d{2})[-_ .]?(\d{2})[-_ .]?(\d{2})(?!\d)"),
           re.compile(r"^\d{3}[-_ ](\d{2})(\d{2})(\d{2})(?!\d)")]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")


def file_date(name):
    for i, rx in enumerate(DATE_RE):
        m = rx.match(name)
        if m:
            y, mo, d = m.groups()
            try:
                return datetime.date(int(y) if i == 0 else 2000 + int(y), int(mo), int(d))
            except ValueError:
                return None
    return None


def norm(t):
    t = re.sub(r"\[[ xX/-]\]|[*_`#>]|\b(todo|to do|done|ok|fait|gedaan|asap)\b", " ", t, flags=re.I)
    return re.sub(r"\W+", " ", t).strip().lower()[:80]


def project_files(root, folder_prefix):
    d = os.path.join(root, folder_prefix)
    out = []
    for dp, _, fs in os.walk(d):
        for f in fs:
            if f.endswith(".md"):
                out.append(os.path.relpath(os.path.join(dp, f), root))
    return out


def match_title(text, projects):
    """The project whose number or name the text carries; None when none does, or when two
    projects tie (a bare "Elia" names several)."""
    t = " " + re.sub(r"[^\w]+", " ", text.lower()) + " "
    scored = []
    for p in projects:
        num = re.match(r"(\d{3})", p["folder"])
        s = 10 if num and re.search(rf"(?<!\d){num.group(1)}(?!\d)", text) else 0
        names = [re.sub(r"^\d{3}[\s_-]*", "", p["folder"])] + [p.get("title") or ""] + list(p.get("aliases") or [])
        best = 0
        for n in names:
            words = {w for w in re.sub(r"[^\w]+", " ", n.lower()).split() if len(w) > 2 and w not in M.STOP}
            hits = sum(1 for w in words if f" {w} " in t)
            if words and hits and hits / len(words) >= 0.5:
                best = max(best, 3 * hits)
        s += best
        if s:
            scored.append((s, p))
    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None
    return scored[0][1]


def domain_index(root, projects, own, cfg_domains=None):
    """{domain: {project folder: count}} from the email addresses in each project's notes."""
    idx = defaultdict(lambda: defaultdict(int))
    for p in projects:
        for f in project_files(root, p["prefix"]):
            try:
                text = open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for d in {m.lower() for m in EMAIL.findall(text)}:
                if d not in PUBLIC and not any(d == o or d.endswith("." + o) for o in own):
                    idx[d][p["folder"]] += 1
    # Declared in config.yaml (briefing.project_domains: {"235 Sapinette": [client.be]}): outweighs the notes.
    for folder, doms in ((cfg_domains or {}).items()):
        for d in doms or []:
            idx[str(d).lower().lstrip("@")][str(folder)] += 100
    return idx


def match_domains(domains, idx, projects):
    votes = defaultdict(int)
    for d in domains or []:
        d = str(d).lower().lstrip("@")
        for folder, n in idx.get(d, {}).items():
            votes[folder] += 1 + min(n, 3) / 10
    if not votes:
        return None
    folder = max(votes, key=votes.get)
    # Ambiguous when two projects share the top vote: a consultant on several projects says nothing.
    if sum(1 for v in votes.values() if v == votes[folder]) > 1:
        return None
    return next(p for p in projects if p["folder"] == folder)


def prep(root, cfg, project, event_day, alias_rx, word_rx):
    b = cfg.get("briefing") or {}
    n = int(b.get("prep_meetings", 3))
    dated = [(file_date(os.path.basename(f)), f) for f in project_files(root, project["prefix"])]
    dated = sorted([(d, f) for d, f in dated if d and d < event_day], reverse=True)[:n]
    meetings = [{"date": d.isoformat(), "link": f} for d, f in dated]
    items, closed = {}, set()
    for d, f in sorted(dated):                      # oldest first, so later notes can close items
        fm, body = split_note(open(os.path.join(root, f), encoding="utf-8", errors="replace").read())
        for ln in body.splitlines():
            t = ln.strip()
            if not t:
                continue
            m = G.TASK.match(ln)
            key = norm(m.group(2) if m else t)
            if not key:
                continue
            if (m and m.group(1) in "xX") or G.DONE.search(t):
                closed.add(key)
                items.pop(key, None)
                continue
            kind = "discuss" if DISCUSS.search(t) and not (m and m.group(1) == " ") else \
                   "open" if (m and m.group(1) == " ") or word_rx.search(t) else None
            if not kind:
                continue
            text = (m.group(2) if m else re.sub(r"^[-*+]\s+|^\d+\.\s+", "", t)).strip()[:240]
            if key in items:
                items[key]["seen"] += 1
                items[key]["last"] = {"date": d.isoformat(), "link": f}
            else:
                items[key] = {"kind": kind, "text": text, "mine": bool(alias_rx.search(t)), "seen": 1,
                              "open_since": d.isoformat(), "last": {"date": d.isoformat(), "link": f}}
    opened = [v for k, v in items.items() if k not in closed]
    decisions = []
    ent = project.get("entity")
    if ent and dated:
        oldest = dated[-1][0].isoformat()
        _, body = split_note(open(os.path.join(root, ent), encoding="utf-8").read())
        sec = re.split(r"(?m)^## Decisions\s*$", body, maxsplit=1)
        if len(sec) == 2:
            for ln in re.split(r"(?m)^## ", sec[1], maxsplit=1)[0].splitlines():
                m = re.match(r"^- (\d{4}-\d{2}-\d{2}),\s*([^:]+):\s*(.*)$", ln.strip())
                if m and m.group(1) >= oldest:
                    decisions.append({"date": m.group(1), "kind": m.group(2), "text": m.group(3)[:300]})
    return {"meetings": meetings, "decisions": decisions,
            "open": [x for x in opened if x["kind"] == "open"],
            "discuss": [x for x in opened if x["kind"] == "discuss"]}


def agenda_url(event, project, meetings):
    paths = ", ".join(m["link"] for m in meetings) or "none found"
    seed = (f"Draft the agenda for the meeting \"{event.get('subject', '')}\" on {str(event.get('start', ''))[:10]} "
            f"for project {project['folder']}. From the augment vault, read the project note {project.get('entity') or ''} "
            f"and the last meeting notes ({paths}); list the open action points with their owners, the items to "
            "discuss, and the decisions to confirm. Done is a short agenda I can paste into the invitation.")
    return "https://claude.ai/new?q=" + urllib.parse.quote(seed)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("vault")
    ap.add_argument("--events", required=True)
    a = ap.parse_args()
    root = os.path.abspath(a.vault)
    if not os.path.isfile(os.path.join(root, M.MARKER)):
        print(f"REFUSED: {root} is not a vault (no {M.MARKER})")
        sys.exit(1)
    cfg = load_config(root)
    b = cfg.get("briefing") or {}
    events = json.load(open(a.events, encoding="utf-8"))
    ents = G.project_entities(root, cfg)
    projects = G.project_names(root, ents, cfg)
    own = [str(x).lower() for x in (b.get("own_domains") or [])]
    if not own and cfg.get("author_email"):
        own = [str(cfg["author_email"]).split("@")[-1].lower()]
    alias_rx, word_rx, _ = G.marker_rx(cfg)
    dom_idx = None
    out = []
    for e in events:
        text = f"{e.get('subject', '')} {e.get('location', '')}"
        p, how = match_title(text, projects), "title"
        if not p and e.get("attendee_domains"):
            if dom_idx is None:
                dom_idx = domain_index(root, projects, own, b.get("project_domains"))
            p, how = match_domains(e["attendee_domains"], dom_idx, projects), "attendees"
        row = {k: e.get(k) for k in ("subject", "start", "end", "location", "all_day", "organiser_is_me")}
        if not p:
            row["project"] = None
            out.append(row)
            continue
        try:
            day = datetime.date.fromisoformat(str(e.get("start", ""))[:10])
        except ValueError:
            day = datetime.date.today()
        facts = prep(root, cfg, p, day, alias_rx, word_rx)
        row.update(project={"folder": p["folder"], "entity": p.get("entity"), "matched_by": how},
                   agenda_url=agenda_url(e, p, facts["meetings"]), **facts)
        out.append(row)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
