#!/usr/bin/env python3
"""Compact augment_wiki/index.jsonl from augment_wiki/history.jsonl (DREAM phase 7).

history.jsonl is the append-only ledger: every STORE, PROCESS, MINT, FLAG and
status change appends a line, so an id appears as many times as it has changed.
index.jsonl is the current-state projection: exactly one line per id, its most
recent state. This script rebuilds that projection deterministically, keep the
last occurrence of each id in file order, so the index is never hand-edited
and never drifts from the ledger (CONTRACT §9; the same re-derivation discipline
the hasher follows).

Run markers (`kind` ending in `_run`: process_run, dream_run, mint_run,
digest_run, harvest_run, sweep_run, verify_run) are audit entries in the ledger
only; they are skipped, never projected into the index. An id whose latest entry
carries `retired: true` is dropped from the projection as well, for tooling state
that has finished (see is_retired). Wiki notes carry a
`type` field and no `kind`, source notes carry `kind: "note"`, and the scope
declaration carries `kind: "scope"`, all three are real state and are kept.

Written atomically (temp file + os.replace) so a crash mid-write cannot leave a
truncated index. Run from the vault root.

First it merges augment_wiki/history.pending/: ledger entries the remote
connector wrote, one small file per write, because GitHub cannot append to a
file. They are appended to history.jsonl in file-name order (each name starts
with its timestamp) and the merged files are removed: they are transport, not
records, and every line they carried now stands in the ledger.

Usage is the second ledger. augment_wiki/usage.pending/, written by
`usage_log.py` and the connector, is merged the same way into the append-only
augment_wiki/usage.jsonl, and each wiki note's index entry is given a `used`
field, `{"opens", "cites", "last_opened", "last_cited"}`, recomputed from that
ledger on every run and absent when the note was never used. A reader therefore
never writes the index; it drops a file, and this script projects it.
"""
import _cli
import json, os, sys, tempfile

ROOT = _cli.vault_arg()
HIST = os.path.join(ROOT, "augment_wiki/history.jsonl")
IDX = os.path.join(ROOT, "augment_wiki/index.jsonl")
PENDING = os.path.join(ROOT, "augment_wiki/history.pending")
USAGE = os.path.join(ROOT, "augment_wiki/usage.jsonl")
USAGE_PENDING = os.path.join(ROOT, "augment_wiki/usage.pending")


def merge_pending(pending=PENDING, target=HIST):
    """Append the parked files in `pending` to `target`, then remove them. Returns the line count."""
    if not os.path.isdir(pending):
        return 0
    files = sorted(f for f in os.listdir(pending) if f.endswith(".jsonl"))
    lines = []
    for f in files:
        for line in open(os.path.join(pending, f), encoding="utf-8"):
            if line.strip():
                json.loads(line)          # a torn file stops the merge before anything is written
                lines.append(line.rstrip("\n") + "\n")
    if lines:
        gap = False
        if os.path.exists(target):
            with open(target, "rb") as h:
                h.seek(0, 2)
                gap = h.tell() and (h.seek(-1, 2) or h.read(1) != b"\n")
        with open(target, "a", encoding="utf-8", newline="\n") as h:
            if gap:
                h.write("\n")
            h.writelines(lines)
    for f in files:
        os.remove(os.path.join(pending, f))
    if not os.listdir(pending):
        os.rmdir(pending)
    return len(lines)


def usage_by_id(path=USAGE):
    """{id: {"opens", "cites", "applies", "last_opened", "last_cited", "last_applied"}} from the usage ledger."""
    out = {}
    if not os.path.exists(path):
        return out
    for line in open(path, encoding="utf-8"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        kind, i, at = d.get("kind"), d.get("id"), str(d.get("at", ""))
        if not i or kind not in ("open", "cite", "apply"):
            continue
        u = out.setdefault(i, {})
        n, last = {"open": ("opens", "last_opened"), "cite": ("cites", "last_cited"),
                   "apply": ("applies", "last_applied")}[kind]
        u[n] = u.get(n, 0) + 1
        if at > u.get(last, ""):
            u[last] = at
    return out


def is_run_marker(entry):
    return str(entry.get("kind", "")).endswith("_run")


def is_retired(entry):
    """Tooling state whose job is finished, dropped from the projection.

    This is not a deletion and does not touch "never delete" (CONTRACT §9): every
    line the id ever had stays in the ledger, and only the current-state projection
    stops carrying it, which is the whole point of splitting the two. It exists for
    state that is real while a pass is running and duplicated bookkeeping once it
    is not, the RESTYLE queue being the case: mid-pass it is the only record of
    which notes are rebuilt, and closed it says nothing history does not already
    hold in the per-note lines and the `restyle_run` markers.
    """
    return entry.get("retired") is True


def main():
    merged = merge_pending()
    if merged:
        print(f"merged {merged} pending ledger line(s) from the connector into history.jsonl")
    used_merged = merge_pending(USAGE_PENDING, USAGE)
    if used_merged:
        print(f"merged {used_merged} usage line(s) into usage.jsonl")
    usage = usage_by_id()
    latest = {}          # id -> most recent entry
    order = []           # first-seen order of ids, for a stable index
    seen = set()
    kept = skipped = 0
    with open(HIST, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            if is_run_marker(entry):
                skipped += 1
                continue
            i = entry.get("id")
            if i is None:
                continue
            if i not in seen:
                seen.add(i); order.append(i)
            latest[i] = entry
            kept += 1

    retired = {i for i, e in latest.items() if is_retired(e)}
    order = [i for i in order if i not in retired]

    tmp_fd, tmp_path = tempfile.mkstemp(dir=os.path.dirname(IDX) or ".", suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as out:
            for i in order:
                e = dict(latest[i])
                e.pop("used", None)          # usage is projected here only, never carried from a ledger line
                if i in usage and i.startswith("augment_wiki/"):
                    e["used"] = usage[i]
                out.write(json.dumps(e, ensure_ascii=False) + "\n")
        os.replace(tmp_path, IDX)
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    print(f"compacted index: {len(order)} entries "
          f"({kept} ledger lines folded, {skipped} run-markers skipped, "
          f"{len(retired)} retired)")


if __name__ == "__main__":
    main()
