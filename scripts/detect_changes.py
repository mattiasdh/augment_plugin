#!/usr/bin/env python3
"""Detect changed inputs for DREAM phase 1 (CONTRACT §9).

Compares every indexed source's current content hash against the stored one and
reports drift, plus indexed sources whose file has gone missing. Mechanical and
pinned: run this, never re-derive the comparison by hand each cycle. A hand pass
miscounts (a prior run logged 376 sources checked when the index held 454), and
a reimplemented hash silently disagrees on line-ending or trailing-newline
handling and raises false staleness, the exact CONTRACT §9 trap; this reuses
`hash_source.content_hash`, the one canonical implementation.

Metadata edits do not drift: the canonical hash excludes the frontmatter
whole, so retagging a source or writing its backlinks is not a change.

A missing source whose hash matches a current file elsewhere under its own
scope path is reported `LIKELY RENAME`, not bare `MISSING`, so a sweep does
not have to re-derive the same glob-and-hash check by hand every time a
folder gets reorganised. This never resolves the rename; recording one stays
VERIFY's call (§9), never a guess. It only saves the hand check, and only
where the match is unambiguous: exactly one same-basename candidate with the
matching hash, or, when no file keeps the basename, exactly one unindexed file
under the scope path carrying the hash (a move that also renamed, found
2026-09-25). Anything else, zero matches or more than one, reports plain
`MISSING` and leaves the judgement untouched.

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
import glob, json, os, sys
import yaml
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


def scope_root(path, config):
    """The longest scope-rule path governing `path`, or its top-level folder if
    no rule matches more specifically. The search root for a likely-rename glob:
    narrow enough that an unrelated project's same-named file never collides,
    the same longest-prefix precedence `_gen_util.scope_of` uses for in/out."""
    sc = (config or {}).get("scope") or {}
    best = None
    for r in sc.get("rules", []):
        d = str(r.get("path", ""))
        if (path == d or path.startswith(d + "/")) and (
                best is None or len(d) > len(best)):
            best = d
    return best or path.split("/")[0]


def likely_rename(missing_id, missing_hash, root, config, indexed=None):
    """The single current file, if any, carrying `missing_id`'s recorded hash under
    its scope path. None where the match is not unambiguous.

    A same-basename match is tried first. When there is none, a move that also
    renamed the file (`26-06 X.md` to `C26-06 X/C26-06 X.md`) is found by its
    content hash alone, among files under the same scope path that the index
    does not already know, since an indexed file with the same body is a
    duplicate of another source rather than this one's new home."""
    base = os.path.basename(missing_id)
    search = os.path.join(root, scope_root(missing_id, config))
    cands = [p for p in glob.glob(os.path.join(search, "**", base), recursive=True)
             if os.path.isfile(p)]
    matches = [p for p in cands if content_hash(p) == missing_hash]
    if len(matches) == 1:
        return os.path.relpath(matches[0], root)
    if matches:
        return None
    known = indexed or set()
    matches = [p for p in glob.glob(os.path.join(search, "**", "*.md"), recursive=True)
               if os.path.isfile(p) and os.path.relpath(p, root) not in known
               and content_hash(p) == missing_hash]
    if len(matches) == 1:
        return os.path.relpath(matches[0], root)
    return None


def main():
    idx = [json.loads(l) for l in open(IDX, encoding="utf-8") if l.strip()]
    src_entries = [e for e in idx if is_source_entry(e)]
    retired = sum(1 for e in idx if e.get("status") in ("deleted", "renamed"))
    cfg_path = os.path.join(ROOT, "augment_wiki/config.yaml")
    config = yaml.safe_load(open(cfg_path, encoding="utf-8")) if os.path.exists(cfg_path) else {}

    drift, missing = [], []
    for e in src_entries:
        p = os.path.join(ROOT, e["id"])
        if not os.path.exists(p):
            missing.append(e)
            continue
        cur = content_hash(p)
        if cur != e["hash"]:
            drift.append((e["id"], e["hash"], cur, e.get("produced", [])))

    for i, old, new, prod in drift:
        print(f"DRIFT {old} -> {new}  {i}  produced={prod}")
    for e in missing:
        renamed_to = likely_rename(e["id"], e["hash"], ROOT, config,
                                   {x["id"] for x in idx})
        if renamed_to:
            print(f"LIKELY RENAME -> {renamed_to}  {e['id']}")
        else:
            print(f"MISSING  {e['id']}")
    print(f"changed-inputs: {len(drift)} drift, {len(missing)} missing, "
          f"{len(src_entries)} sources checked"
          + (f", {retired} retired paths (deleted or renamed, not checked)" if retired else ""))



if __name__ == "__main__":
    main()
