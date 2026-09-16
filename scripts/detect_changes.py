#!/usr/bin/env python3
"""Detect changed inputs for DREAM phase 1 (CONTRACT §9).

Compares every indexed source's current content hash against the stored one and
reports drift, plus indexed sources whose file has gone missing. Mechanical and
pinned: run this, never re-derive the comparison by hand each cycle. A hand pass
miscounts (a prior run logged 376 sources checked when the index held 454), and
a reimplemented hash silently disagrees on line-ending or trailing-newline
handling and raises false staleness, the exact CONTRACT §9 trap; this reuses
`hash_source.content_hash`, the one canonical implementation.

Declaration-only edits do not drift: the canonical hash already excludes the
`Status`, `updated` and `assisted_by` lines, so retagging a source is not a
change.

A source the person has removed is recorded `status: deleted` in the index, and
one they renamed leaves its old path recorded `status: renamed` beside the new
entry (CONTRACT §5). Neither is reported missing again: both are accounted for. Keeping the
two apart is the point of the state. An unrecorded missing file is a real finding,
a sync that dropped a note or a rename nobody logged, and if every deleted file
kept reporting itself forever, that genuine loss would sit unnoticed in a standing
list of expected ones. Exit is always 0, because drift is the normal signal that drives
rebuilds, not an error to gate on (conformance is the gate). The output is a
line per drift and per missing file, then a summary line the cycle reads.

Run from the vault root; the argument `.` is the vault root.
"""
import json, os, sys
from hash_source import content_hash

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
IDX = os.path.join(ROOT, "augment_wiki/index.jsonl")


def is_source_entry(e):
    """A live source ledger entry: carries a content hash, is not a wiki note, is not
    the scope record, and is not a path the person has retired by deleting or
    renaming it (§5)."""
    i = str(e.get("id", ""))
    return (bool(e.get("hash")) and not i.startswith("augment_wiki/")
            and e.get("status") not in ("deleted", "renamed"))


def main():
    idx = [json.loads(l) for l in open(IDX, encoding="utf-8") if l.strip()]
    src_entries = [e for e in idx if is_source_entry(e)]
    retired = sum(1 for e in idx if e.get("status") in ("deleted", "renamed"))

    drift, missing = [], []
    for e in src_entries:
        p = os.path.join(ROOT, e["id"])
        if not os.path.exists(p):
            missing.append(e["id"])
            continue
        cur = content_hash(p)
        if cur != e["hash"]:
            drift.append((e["id"], e["hash"], cur, e.get("produced", [])))

    for i, old, new, prod in drift:
        print(f"DRIFT {old} -> {new}  {i}  produced={prod}")
    for i in missing:
        print(f"MISSING  {i}")
    print(f"changed-inputs: {len(drift)} drift, {len(missing)} missing, "
          f"{len(src_entries)} sources checked"
          + (f", {retired} retired paths (deleted or renamed, not checked)" if retired else ""))


if __name__ == "__main__":
    main()
