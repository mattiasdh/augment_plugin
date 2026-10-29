#!/usr/bin/env python3
"""Session records: `augment_sessions/<id>.md` (reference/sessions.md).

A record is the working state of one conversation, written so that a fresh session on
any surface (Chat, Cowork, Code) can pick the work up again: its goal, where it stands,
the next steps, what it touched, and a prompt to resume from. One file per session,
replaced by every later RECORD of the same session; git keeps the earlier versions, so
the replacement is the supersession. State, never a transcript.

The key is an id the first RECORD mints, `R-YYMMDD-xxxx`, because Chat shows Claude
neither its conversation id nor its title, and titles change. Where the surface has a
session id (Code, Cowork), it is stored too, and a RECORD that names it without an id
finds its own record again, so the key survives a compaction.

    record_write.py <vault> write [--id ID] [--title T] [--status open|parked|closed]
                                  [--project P] [--surface S] [--session-id SID] [--session-url URL]
                                  (--body-file F | --body TEXT) [--by producer/version]
    record_write.py <vault> status ID open|parked|closed [--by ...]
    record_write.py <vault> get ID
    record_write.py <vault> list [--status open|parked|closed|all]
    record_write.py <vault> search WORDS... [--status ...]

The body carries five sections, in this order: `## Goal`, `## State`, `## Next steps`,
`## Touched`, `## Resume`. Through the connector the same writes are `record_write`,
`record_get` and `record_search`, held to this file by a parity test.
"""
import _cli
import argparse, os, random, re, sys
_cli.help_guard()

import _memory as M
from _gen_util import stamp

DIR = "augment_sessions"
ORDER = ["id", "title", "status", "project", "surface", "session_id", "session_url", "created", "updated", "records", "by"]
QUOTED = ("title", "project")
STATUSES = ("open", "parked", "closed")
SECTIONS = ("Goal", "State", "Next steps", "Touched", "Resume")
BODY_MAX = 8000          # a working state; past this it has become a transcript or a note
ID_RE = re.compile(r"^R-\d{6}-[a-z2-7]{4}$")
ALPHABET = "abcdefghijklmnopqrstuvwxyz234567"
URL_RE = re.compile(r"^https://claude\.ai/\S+$")


def url_of(session_id):
    """The web address of a cloud Code session, from its `cse_` id; None for anything else."""
    m = re.fullmatch(r"cse_([A-Za-z0-9]+)", str(session_id or ""))
    return f"https://claude.ai/code/session_{m.group(1)}" if m else None


class Refused(Exception):
    pass


def render(fm, body):
    lines = ["---"]
    for k in ORDER:
        v = fm.get(k)
        if v is None or v == "":
            continue
        lines.append(f"{k}: {M.q(v)}" if k in QUOTED else f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n" + body.strip("\n") + "\n"


def check_body(body):
    """The reason a body is refused, or None."""
    b = (body or "").strip()
    if not b:
        return "a record needs its body (the five sections)"
    if len(b) > BODY_MAX:
        return (f"{len(b)} characters; {BODY_MAX} at most. A record is the working state, not a "
                "transcript: decisions and findings belong in the notes (write), and the record links them")
    heads = [m.group(1).strip() for m in re.finditer(r"^## +(.+?)\s*$", b, re.M)]
    found = [h for h in heads if h in SECTIONS]
    missing = [s for s in SECTIONS if s not in found]
    if missing:
        return "missing section(s): " + ", ".join(f"## {s}" for s in missing)
    if found != list(SECTIONS):
        return "sections out of order; they run " + " / ".join(SECTIONS)
    hit = M.secret_in(b)
    if hit:
        return f"that looks like a secret ({hit}); a record never holds one"
    return None


def mint(root, today=None):
    d = (today or stamp()[:10]).replace("-", "")[2:]
    for _ in range(50):
        i = f"R-{d}-" + "".join(random.choice(ALPHABET) for _ in range(4))
        if not os.path.exists(path_of(root, i)):
            return i
    raise Refused("could not mint a free id")


def path_of(root, rid):
    return os.path.join(root, DIR, f"{rid}.md")


def load(root):
    """Every record as (id, frontmatter, body), newest update first."""
    d = os.path.join(root, DIR)
    out = []
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.endswith(".md") and ID_RE.match(f[:-3]):
                fm, body = M.split_note(open(os.path.join(d, f), encoding="utf-8").read())
                out.append((f[:-3], fm, body))
    out.sort(key=lambda r: str(r[1].get("updated", "")), reverse=True)
    return out


def line(rid, fm):
    proj = f"  [{fm['project']}]" if fm.get("project") else ""
    return f"{rid}  {fm.get('status', '?'):6}  {fm.get('updated', '?')}{proj}  {fm.get('title', '')}"


def search(root, words, status="all"):
    qt = M.tokens(" ".join(words))
    hits = []
    for rid, fm, body in load(root):
        if status != "all" and fm.get("status") != status:
            continue
        if any(w.strip() in (rid, str(fm.get("session_id", ""))) for w in words):
            hits.append((100, rid, fm))
            continue
        head = M.tokens(f"{fm.get('title', '')} {fm.get('project', '')}")
        rest = M.tokens(body)
        s = sum(3 * (t in head) + (t in rest) for t in qt)
        if s:
            hits.append((s, rid, fm))
    hits.sort(key=lambda h: (h[0], str(h[2].get("updated", ""))), reverse=True)
    return hits


def write(root, a):
    rid = a.id
    cur_fm, cur_body = {}, ""
    if rid:
        if not ID_RE.match(rid):
            raise Refused(f"{rid!r} is not a record id (R-YYMMDD-xxxx)")
        if not os.path.exists(path_of(root, rid)):
            raise Refused(f"no record {rid}; omit --id to start a new one, or search for the right id")
    elif a.session_id:
        mine = [r for r in load(root) if str(r[1].get("session_id", "")) == a.session_id]
        if mine:
            rid = mine[0][0]
    if rid:
        cur_fm, cur_body = M.split_note(open(path_of(root, rid), encoding="utf-8").read())
    body = open(a.body_file, encoding="utf-8").read() if a.body_file else a.body
    why = check_body(body)
    if why:
        raise Refused(why)
    if a.session_url and not URL_RE.match(a.session_url):
        raise Refused("session_url is the conversation's claude.ai address (https://claude.ai/...)")
    title = a.title or cur_fm.get("title")
    if not title:
        raise Refused("a new record needs --title")
    if a.status and a.status not in STATUSES:
        raise Refused(f"status is one of {', '.join(STATUSES)}")
    now = a.now or stamp()
    new = not rid
    if new:
        rid = mint(root, now[:10])
    fm = {
        "id": rid, "title": title, "status": a.status or cur_fm.get("status") or "open",
        "project": a.project or cur_fm.get("project"), "surface": a.surface or cur_fm.get("surface"),
        "session_id": a.session_id or cur_fm.get("session_id"),
        "session_url": a.session_url or url_of(a.session_id) or cur_fm.get("session_url") or url_of(cur_fm.get("session_id")),
        "created": cur_fm.get("created") or now, "updated": now,
        "records": (int(cur_fm.get("records", 0) or 0) + 1) if not new else 1, "by": a.by,
    }
    os.makedirs(os.path.join(root, DIR), exist_ok=True)
    open(path_of(root, rid), "w", encoding="utf-8", newline="\n").write(render(fm, body))
    rel = f"{DIR}/{rid}.md"
    if new:
        return f"RECORD {rid} created ({rel}). Quote this id to resume or update it from any surface."
    return f"RECORD {rid} updated, version {fm['records']}, superseding the state of {cur_fm.get('updated', '?')} ({rel})."


def set_status(root, rid, status, by, now=None):
    if status not in STATUSES:
        raise Refused(f"status is one of {', '.join(STATUSES)}")
    p = path_of(root, rid)
    if not ID_RE.match(rid or "") or not os.path.exists(p):
        raise Refused(f"no record {rid}")
    fm, body = M.split_note(open(p, encoding="utf-8").read())
    fm.update(status=status, updated=now or stamp(), by=by)
    open(p, "w", encoding="utf-8", newline="\n").write(render(fm, body))
    return f"RECORD {rid} is now {status}."


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("vault")
    ap.add_argument("cmd", choices=["write", "status", "get", "list", "search"])
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--id")
    ap.add_argument("--title")
    ap.add_argument("--status")
    ap.add_argument("--project")
    ap.add_argument("--surface")
    ap.add_argument("--session-id")
    ap.add_argument("--session-url", help="the conversation's claude.ai address; derived for Code sessions")
    ap.add_argument("--body")
    ap.add_argument("--body-file")
    ap.add_argument("--by", default="augment/claude-code")
    ap.add_argument("--now", help=argparse.SUPPRESS)       # tests: a fixed stamp
    a = ap.parse_args()
    root = os.path.abspath(a.vault)
    if not os.path.isfile(os.path.join(root, M.MARKER)):
        print(f"REFUSED: {root} is not a vault (no {M.MARKER})")
        sys.exit(1)
    try:
        if a.cmd == "write":
            print(write(root, a))
        elif a.cmd == "status":
            if len(a.rest) != 2:
                raise Refused("status takes ID and open|parked|closed")
            print(set_status(root, a.rest[0], a.rest[1], a.by, a.now))
        elif a.cmd == "get":
            if not a.rest or not os.path.exists(path_of(root, a.rest[0])) or not ID_RE.match(a.rest[0]):
                raise Refused(f"no record {a.rest[0] if a.rest else '(none given)'}; search for it")
            print(open(path_of(root, a.rest[0]), encoding="utf-8").read(), end="")
        elif a.cmd == "list":
            st = a.status or "live"
            rows = [r for r in load(root) if st == "all" or (st == "live" and r[1].get("status") != "closed")
                    or r[1].get("status") == st]
            print("\n".join(line(r[0], r[1]) for r in rows) or "no records")
        else:
            if not a.rest:
                raise Refused("search needs words (an id, a title word, a project, a file name)")
            hits = search(root, a.rest, a.status or "all")
            print("\n".join(f"{s:3}  {line(rid, fm)}" for s, rid, fm in hits) or "no record matches")
    except Refused as e:
        print(f"REFUSED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
