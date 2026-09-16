#!/usr/bin/env python3
"""Append declined convergence pairs to `augment_wiki/relations_dismissed.jsonl`.

The sidecar is what stops a declined pair resurfacing (CONTRACT §12). Until this
script existed it was appended by hand, in the middle of judging a batch, with
nothing checking whether the pair was already there: by 2026-09-08 the file held
380 lines for 374 pairs, six of them dismissed twice on different nights. No pair
was ever re-judged from it (`gen_relations.py` excludes on the sorted tuple, so a
duplicate is inert), but a write path with no read before it is one bad line away
from mattering, and the fix belongs where the write happens rather than in a rule
telling the next session to look first.

So: this reads the sidecar, skips any pair it already carries under the same
ruling, and reports what it skipped. A pair may legitimately appear twice under
*different* rulings, since declining to create an edge and declining to remove one
are opposite answers about one pair, and those are kept apart.

Usage, from the vault root:

    dismiss_pairs.py . --note "why" slugA::slugB [slugC::slugD ...]
    dismiss_pairs.py . --keep --note "why" slugA::slugB     # a declined *removal*
    dismiss_pairs.py . --dry-run --note "why" slugA::slugB

`--note` is required and is the reason, in the person's terms, written onto every
pair in the call; a batch of declines sharing one shape shares one note. Pass the
call more than once where the reasons differ.
"""
import json, os, sys

ROOT = ([a for a in sys.argv[1:] if not a.startswith("--")] or ["."])[0]
ARGS = sys.argv[1:]
KEEP = "--keep" in ARGS
DRY = "--dry-run" in ARGS
PATH = os.path.join(ROOT, "augment_wiki/relations_dismissed.jsonl")


def parse_args(argv):
    note, pairs, i = None, [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--note":
            i += 1
            note = argv[i] if i < len(argv) else None
        elif "::" in a:
            x, y = a.split("::", 1)
            if not x or not y:
                sys.exit(f"malformed pair: {a}")
            pairs.append([x, y])
        i += 1
    return note, pairs


def existing(path):
    """Pairs already on file, as {(sorted tuple, ruling)}."""
    have = set()
    if not os.path.exists(path):
        return have
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        pr = rec.get("pair")
        if pr and len(pr) == 2:
            have.add((tuple(sorted(pr)), rec.get("ruling") or "no-link"))
    return have


def main():
    note, pairs = parse_args(ARGS[1:] if ARGS and not ARGS[0].startswith("--") else ARGS)
    if not pairs:
        sys.exit("no pairs given (expected slugA::slugB)")
    if not note:
        sys.exit("--note is required: a declined pair with no recorded reason is a "
                 "decision nobody can review")
    ruling = "keep" if KEEP else "no-link"
    have = existing(PATH)
    today = __import__("datetime").date.today().isoformat()

    new, dupes = [], []
    for pr in pairs:
        key = (tuple(sorted(pr)), ruling)
        if key in have:
            dupes.append(pr)
            continue
        have.add(key)
        rec = {"pair": pr, "ruled": today, "note": note}
        if KEEP:
            rec["ruling"] = "keep"
        new.append(rec)

    for rec in new:
        print(("would record " if DRY else "recorded ") +
              f"{rec['pair'][0]} / {rec['pair'][1]}" + (" (keep)" if KEEP else ""))
    for pr in dupes:
        print(f"already on file, skipped: {pr[0]} / {pr[1]}")

    if new and not DRY:
        with open(PATH, "a", encoding="utf-8") as f:
            for rec in new:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"{'dry run: ' if DRY else ''}{len(new)} recorded, {len(dupes)} skipped as duplicate")


if __name__ == "__main__":
    main()
