#!/usr/bin/env python3
"""A skill's own memory: `<skills root>/<skill>/MEMORY.md` (reference/skills.md).

Every skill that learns from use keeps one MEMORY.md beside its references: the
current lessons as short facts, read at the start of every run (Preflight) and
rewritten at the end when something new was learned. It is how a skill improves
across Chat, Code and Cowork whether or not the skill itself is loaded, without a
second registry: the sweep promotes settled lessons into `references/` with the
person's approval and trims the file, so MEMORY.md stays small and recent.

It holds how the skill's work is done (a tool's behaviour, a version gap, an error
and its workaround, a convention the person set for this skill's output), never
project or domain facts, which go to the notes, and never secrets. The same
3000-character cap and secret refusal as a memory card apply. Replacing the body is
the write: it is current state, not a log, and the commit history keeps the past.

    skill_memory.py <vault> get <skill>                      print it (and record an open)
    skill_memory.py <vault> set <skill> --body-file F [--by augment/claude-code]
    skill_memory.py <vault> set <skill> --body "text"        replace the lessons
    skill_memory.py <vault> seen <skill>                     it proved right in use
    skill_memory.py <vault> list                             every skill and its memory state

Through the connector the same writes are `skill_memory_get` and `skill_memory_update`.
"""
import _cli
import argparse, os, subprocess, sys
_cli.help_guard()

import _memory as M
from _gen_util import skills_root

ORDER = ["skill", "updated", "seen", "by"]


def fail(msg):
    print(f"REFUSED: {msg}")
    sys.exit(1)


def skill_dir(root, skill):
    sr = skills_root(root)
    if not sr:
        fail("config.yaml declares no skills root (skills: root:)")
    if not skill or "/" in skill or skill.startswith((".", "_")):
        fail(f"{skill!r} is not a skill folder name")
    d = os.path.join(root, sr, skill)
    if not os.path.isfile(os.path.join(d, "SKILL.md")):
        fail(f"no skill {skill} under {sr}/ (no SKILL.md)")
    return d


def render(fm, body):
    lines = ["---"] + [f"{k}: {fm[k]}" for k in ORDER if fm.get(k) not in (None, "")] + ["---"]
    return "\n".join(lines) + "\n" + body.strip("\n") + "\n"


def read(path):
    if not os.path.isfile(path):
        return {}, ""
    return M.split_note(open(path, encoding="utf-8").read())


def record(root, kind, path):
    """Usage, as usage_log.py records it; silent on any failure."""
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        subprocess.run([sys.executable, os.path.join(here, "usage_log.py"), root, "--kind", kind,
                        "--op", "skill_memory", os.path.relpath(path, root)],
                       capture_output=True, timeout=20)
    except Exception:
        pass


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("vault")
    ap.add_argument("cmd", choices=["get", "set", "seen", "list"])
    ap.add_argument("skill", nargs="?")
    ap.add_argument("--body")
    ap.add_argument("--body-file")
    ap.add_argument("--by", default="augment/claude-code")
    a = ap.parse_args()
    root = os.path.abspath(a.vault)

    if a.cmd == "list":
        sr = skills_root(root)
        base = os.path.join(root, sr) if sr else ""
        if not base or not os.path.isdir(base):
            fail("no skills root")
        for d in sorted(os.listdir(base)):
            if d.startswith((".", "_")) or not os.path.isfile(os.path.join(base, d, "SKILL.md")):
                continue
            fm, body = read(os.path.join(base, d, "MEMORY.md"))
            state = f"updated {fm.get('updated', '?')}, {len(body.strip())} chars" if body.strip() else "no memory"
            print(f"{d:32} {state}")
        return

    d = skill_dir(root, a.skill)
    p = os.path.join(d, "MEMORY.md")
    fm, body = read(p)

    if a.cmd == "get":
        if not body.strip():
            print(f"{a.skill}: no memory yet ({os.path.relpath(p, root)})")
            return
        record(root, "open", p)
        print(render(fm, body), end="")
        return

    if a.cmd == "seen":
        if not body.strip():
            fail(f"{a.skill} has no memory to confirm")
        fm["seen"] = M.seen_of(fm) + 1
        fm["updated"] = M.stamp()
        open(p, "w", encoding="utf-8", newline="\n").write(render(fm, body))
        record(root, "apply", p)
        print(f"{a.skill}: seen {fm['seen']}")
        return

    new = open(a.body_file, encoding="utf-8").read() if a.body_file else a.body
    if not new or not new.strip():
        fail("set needs the lessons as --body or --body-file")
    if len(new.strip()) > M.BODY_MAX:
        fail(f"{len(new.strip())} characters; {M.BODY_MAX} at most. Promote settled lessons into the skill's "
             "references/ (with the person's approval) and keep MEMORY.md to what is recent.")
    hit = M.secret_in(new)
    if hit:
        fail(f"that looks like a secret ({hit}); memory never holds one")
    fm = {"skill": a.skill, "updated": M.stamp(), "seen": M.seen_of(fm) if fm else 1, "by": a.by}
    open(p, "w", encoding="utf-8", newline="\n").write(render(fm, new))
    record(root, "apply", p)
    print(f"wrote {os.path.relpath(p, root)} ({len(new.strip())} chars)")


if __name__ == "__main__":
    main()
