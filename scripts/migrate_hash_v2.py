#!/usr/bin/env python3
"""One-time migration: re-stamp a vault's ledger from the v1 content hash to v2.

v1 (before v2026-09-24) excluded five named declaration lines from the hash;
v2 excludes the whole frontmatter (hash_source.py). Every stored hash changes,
so without this pass every source reads as drift and every note as stale.

The pass is refused if any live source has drifted under v1, because then its
stored hash no longer describes the file and translating it would silently
bless an edit nothing was rebuilt from. With --allow-drift a drifted source is
left on its v1 hash, so it still reports as drift under v2 and rebuilds as it
should; everything else is translated.

For each live source whose stored hash equals its current v1 hash, append an
entry carrying the v2 hash. For each wiki note, translate every compiled_from
pair whose hash equals its source's verified v1 hash. Other fields are copied
unchanged, except `auto` and `run`, which are dropped: a migration entry is not
an autonomous write and must not reach the sweep's audit list. Then a marker.
History is appended, never rewritten; run compact_index.py afterwards.

    python3 migrate_hash_v2.py <vault>            # dry run, reports counts
    python3 migrate_hash_v2.py <vault> --apply
"""
import datetime, hashlib, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hash_source import content_hash as v2

_DECL_V1 = re.compile(rb"^(Status|augment|created|updated|assisted_by):")


def v1(path):
    """The pre-v2026-09-24 hash, frozen here so the migration can verify against it."""
    raw = open(path, "rb").read()
    segs = raw.split(b"\n")
    if raw.endswith(b"\n"):
        segs = segs[:-1]
    body = b"".join(s + b"\n" for s in segs if not _DECL_V1.match(s))
    return hashlib.sha256(body).hexdigest()[:8]


def main():
    root = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "."
    apply, allow = "--apply" in sys.argv, "--allow-drift" in sys.argv
    idx = [json.loads(l) for l in open(os.path.join(root, "augment_wiki/index.jsonl"),
                                       encoding="utf-8") if l.strip()]
    live = [e for e in idx if e.get("hash") and not str(e["id"]).startswith("augment_wiki/")
            and e.get("status") not in ("deleted", "renamed")]
    mapping, drift, missing = {}, [], []
    for e in live:
        p = os.path.join(root, e["id"])
        if not os.path.exists(p):
            missing.append(e["id"])
            continue
        if v1(p) != e["hash"]:
            drift.append(e["id"])
            continue
        mapping[e["id"]] = (e["hash"], v2(p))
    print(f"{len(live)} live sources: {len(mapping)} verified, {len(drift)} drifted, "
          f"{len(missing)} missing")
    if drift and not allow:
        for d in drift:
            print("  DRIFT", d)
        sys.exit("refused: resolve the drift first (run the cycle), or pass --allow-drift")

    today = datetime.date.today().isoformat()
    out = []
    for e in live:
        if e["id"] not in mapping:
            continue
        old, new = mapping[e["id"]]
        n = {k: v for k, v in e.items() if k not in ("auto", "run")}
        n["hash"] = new
        n["note"] = f"hash v2 migration {today}: {old} -> {new}, content unchanged."
        out.append(n)
    notes_done = 0
    for e in idx:
        if not str(e["id"]).startswith("augment_wiki/") or not e.get("compiled_from"):
            continue
        cf, changed = [], False
        for pair in e["compiled_from"]:
            m = mapping.get(pair.get("source"))
            if m and pair.get("hash") == m[0]:
                cf.append(dict(pair, hash=m[1]))
                changed = True
            else:
                cf.append(pair)
        if changed:
            n = {k: v for k, v in e.items() if k not in ("auto", "run")}
            n["compiled_from"] = cf
            n["note"] = f"hash v2 migration {today}: compiled_from re-stamped, body unchanged."
            out.append(n)
            notes_done += 1
    out.append({"id": f"migration-run-{today}-hash-v2", "kind": "migration_run", "ran": today,
                "note": (f"Content hash v1 -> v2 (frontmatter excluded whole). {len(mapping)} "
                         f"sources and {notes_done} wiki notes re-stamped; {len(drift)} drifted "
                         f"sources left on v1 to rebuild; {len(missing)} missing left as is.")})
    print(f"{len(mapping)} source entries, {notes_done} note entries, 1 marker")
    if not apply:
        print("dry run; pass --apply to append")
        return
    with open(os.path.join(root, "augment_wiki/history.jsonl"), "a", encoding="utf-8") as f:
        for n in out:
            f.write(json.dumps(n, ensure_ascii=False) + "\n")
    print(f"appended {len(out)} lines; now run compact_index.py")


if __name__ == "__main__":
    main()
