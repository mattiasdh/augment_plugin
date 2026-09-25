#!/usr/bin/env python3
"""Has `history.jsonl` stayed append-only across recent commits, merges included?

The ledger is the one file nothing may rewrite: the index is its projection, so
a line lost from history is a decision lost from the vault. Nothing else notices
the loss. The index recompacts cleanly from whatever history remains, and
detect_changes reports only what that thinner index can see, so a vault can pass
every other check with a day of work silently gone.

The case this exists for happened on 2026-09-24. An editor-side git plugin merged
the remote into a working copy that had diverged, and the merge commit kept the
local tree whole: twelve ledger lines from the other parent, and the notes and
source tags they recorded, disappeared without a conflict marker anywhere. A
merge is the risky shape, because every parent must survive in the child and a
"keep mine" resolution satisfies git while dropping the other side.

For each of the last N commits, and for each of its parents, every line of the
parent's `history.jsonl` must still be present in the child's (as a multiset, so
a merge may interleave appends from both sides). Commits whose blob is identical
to the parent's are skipped without reading.

A loss already dealt with is acknowledged in the ledger itself, by an entry
carrying `"acknowledges": "<commit sha>"`, after its lines have been re-recorded
or ruled unnecessary; an acknowledged commit is no longer reported. The rotation
of history into `history.pre-*.jsonl` is recognised and not reported.

    python3 ledger_guard.py <vault> [--commits N]

Exit 0 clean, 1 on an unacknowledged loss, 2 when git is unavailable.
"""
import collections, json, os, subprocess, sys

PATH = "augment_wiki/history.jsonl"


def _git(root, *args, stdin=None):
    return subprocess.run(["git", *args], cwd=root, input=stdin, capture_output=True,
                          text=True, check=True).stdout


def acknowledged(root):
    acks = set()
    p = os.path.join(root, PATH)
    if not os.path.exists(p):
        return acks
    for line in open(p, encoding="utf-8"):
        if '"acknowledges"' in line:
            try:
                a = json.loads(line).get("acknowledges")
            except json.JSONDecodeError:
                continue
            for sha in (a if isinstance(a, list) else [a]):
                if isinstance(sha, str) and sha:
                    acks.add(sha)
    return acks


def losses(root, max_commits=200):
    """[(commit, parent, lines lost)] for commits that dropped ledger lines."""
    log = _git(root, "log", f"-n{max_commits}", "--format=%H %P").split("\n")
    pairs = [(l.split()[0], l.split()[1:]) for l in log if l.strip()]
    wanted = sorted({c for c, ps in pairs for c in [c, *ps]})
    batch = _git(root, "cat-file", "--batch-check",
                 stdin="".join(f"{c}:{PATH}\n" for c in wanted))
    blob = {}
    for c, line in zip(wanted, batch.splitlines()):
        parts = line.split()
        blob[c] = parts[0] if len(parts) == 3 and parts[1] == "blob" else None
    cache = {}

    def lines(b):
        if b not in cache:
            cache[b] = collections.Counter(l for l in _git(root, "cat-file", "-p", b).split("\n") if l.strip())
        return cache[b]

    rotated, cur = set(), None
    for l in _git(root, "log", f"-n{max_commits}", "--format=@%H", "--name-only").split("\n"):
        if l.startswith("@"):
            cur = l[1:]
        elif l.startswith("augment_wiki/history.pre-") and cur:
            rotated.add(cur)
    acks = acknowledged(root)
    found = []
    for c, ps in pairs:
        if c in rotated or any(c.startswith(a) or a.startswith(c) for a in acks if len(a) >= 7):
            continue
        for p in ps:
            bc, bp = blob.get(c), blob.get(p)
            if not bp or bc == bp:
                continue
            if not bc:
                found.append((c, p, sum(lines(bp).values())))
                continue
            lost = lines(bp) - lines(bc)
            if lost:
                found.append((c, p, sum(lost.values())))
    return found


def main():
    root = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "."
    n = int(sys.argv[sys.argv.index("--commits") + 1]) if "--commits" in sys.argv else 200
    try:
        found = losses(root, n)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"ledger guard: git unavailable or not a repository ({e})")
        sys.exit(2)
    if not found:
        print(f"ledger guard: history.jsonl append-only across the last {n} commits")
        return
    for c, p, k in found:
        subject = _git(root, "log", "-1", "--format=%an, %ad: %s", "--date=short", c).strip()
        print(f"LEDGER LOSS {c[:7]} dropped {k} history line(s) present in parent {p[:7]} ({subject})")
    print("Re-record what was lost (or rule it unnecessary), then append an entry with "
          '"acknowledges": "<sha>" for each commit above.')
    sys.exit(1)


if __name__ == "__main__":
    main()
