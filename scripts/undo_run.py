#!/usr/bin/env python3
"""Lift an autonomous cycle's writes back out, by run id (CONTRACT §12).

DREAM applies its own convergence and anchoring verdicts now, without waiting for
confirmation, which trades a night's delay for an error rate: the cycle's proposals
ran at roughly nine in ten approved over the three sweeps before autonomy was
granted, so about one write a night is one the person would have declined. That
trade only holds while the tenth write is cheap to undo, and "cheap" has to mean one
command against a batch, not a hand-audit of twenty notes.

So every autonomous write carries `"auto": true` and a `"run"` id in its history
entry (`apply_keywords.py --auto --run`), and this reads them back:

    undo_run.py . dream-run-2026-09-13              # revert that night's keyword writes
    undo_run.py . dream-run-2026-09-13 --dry-run    # say what it would revert
    undo_run.py . dream-run-2026-09-13 --only some-note::some-anchor  # one write, not the batch

**It reverts tags, and only reports mints.** A keyword is unsourced and carries no
claim, so removing one restores the prior state exactly (§7). A minted note is a
compiled artefact with sources behind it and possibly tags pointing at it, and
CONTRACT's never-delete rule is not suspended because the cycle rather than a person
wrote it: retiring one is a supersession, which is the person's call at VERIFY (§2).
This prints those for that decision rather than making it.

The reverting write is itself recorded, as an ordinary confirmed removal rather than
an autonomous one, because the person asked for it.
"""
import json, os, re, subprocess, sys

GAINED = re.compile(r"Keyword \[\[([^\]]+)\]\] gained")
HERE = os.path.dirname(os.path.abspath(__file__))


def base(i):
    return os.path.splitext(os.path.basename(str(i)))[0]


def main():
    args = [a for a in sys.argv[1:]]
    dry = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]
    only = None
    if "--only" in args:
        i = args.index("--only")
        only = args[i + 1]
        del args[i:i + 2]
    pos = [a for a in args if not a.startswith("--")]
    if len(pos) < 2:
        sys.exit("usage: undo_run.py . <run-id> [--only slugA::slugB] [--dry-run]")
    root, run = pos[0], pos[1]

    hist = os.path.join(root, "augment_wiki/history.jsonl")
    pairs, mints = [], []
    for line in open(hist, encoding="utf-8"):
        if not line.strip():
            continue
        d = json.loads(line)
        if d.get("run") != run or not d.get("auto"):
            continue
        slug = base(d.get("id"))
        note = str(d.get("note", ""))
        if d.get("kind") == "mint" or note.startswith("MINT"):
            mints.append((d.get("id"), note))
            continue
        for target in GAINED.findall(note):
            pairs.append((slug, target))

    if only:
        want = tuple(only.split("::", 1))
        pairs = [p for p in pairs if p == want]
        if not pairs:
            sys.exit(f"error: {only!r} is not an autonomous write of run {run!r}")

    if not pairs and not mints:
        sys.exit(f"nothing to undo: run {run!r} recorded no autonomous writes")

    for a, b in pairs:
        print(f"{a} loses Keyword: {b}  (applied by {run})")
    for nid, note in mints:
        print(f"MINT, not reverted: {nid}\n    {note[:160]}")
    if mints:
        print("a minted note is superseded at VERIFY, never deleted here (CONTRACT §2)")
    if dry:
        print(f"dry run: {len(pairs)} tag(s) would be removed, nothing written")
        return
    if not pairs:
        return

    cmd = [sys.executable, os.path.join(HERE, "apply_keywords.py"), root, "--remove",
           "--reason", f"Reverted at the person's request: applied without confirmation by {run}, "
                       f"undone with undo_run.py.",
           "--run", f"undo-{run}"] + [f"{a}::{b}" for a, b in pairs]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
