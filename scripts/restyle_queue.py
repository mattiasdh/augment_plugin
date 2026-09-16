#!/usr/bin/env python3
"""Read and advance the RESTYLE queue (PROCESS's RESTYLE mode, CONTRACT §9).

While a pass is open, state is one `restyle` entry in the index holding the ordered
`pending` list, the `done` list and the `batch` size. Every write goes to
`history.jsonl` first and the index is refreshed by compaction, like any other entry:
mid-pass this is the only record of which notes have been rebuilt, so losing it would
cost the pass. Once the queue empties, that stops being true, since the per-note
history lines and the `restyle_run` markers hold the same answer; `close` therefore
retires the id out of the index rather than leaving a summary behind to go stale.

Scheduling deliberately does NOT use `#stale`. That status means a note's sources
moved (CONTRACT §5); borrowing it here would make phase 1 of every later cycle report
drift that does not exist.

    restyle_queue.py . init [--batch N]   # queue every content note, ordered
    restyle_queue.py . next               # ids of the next batch, one per line
    restyle_queue.py . done <id> [<id>…]  # move ids to done, after their history lines
    restyle_queue.py . batch N            # change the batch size
    restyle_queue.py . status             # dormant is a normal answer, not an error
    restyle_queue.py . close              # retire a finished queue out of the index
"""
import datetime, json, os, sys

TODAY = datetime.date.today().isoformat()
TYPES = ("concept", "entity", "tension")     # themes are generated, hubs and views too


def paths(root):
    return os.path.join(root, "augment_wiki/index.jsonl"), os.path.join(root, "augment_wiki/history.jsonl")


def load(root):
    """Entries from the index, but the queue itself from the tail of history.

    History is the authoritative ledger and the index is a projection of it (CONTRACT
    §9), so reading the queue from the index means two commands in a row lose the
    first: `done` appends its line, `batch` reads the not-yet-compacted index and
    writes the stale lists back over it. Read the ledger and that cannot happen.
    """
    idx, hist = paths(root)
    entries = [json.loads(l) for l in open(idx, encoding="utf-8") if l.strip()]
    q = None
    if os.path.exists(hist):
        for l in open(hist, encoding="utf-8"):
            if not l.strip():
                continue
            e = json.loads(l)
            if e.get("id") == "restyle":
                q = e
    if q and q.get("retired"):
        q = None          # a retired queue is gone, not an empty one
    return entries, q


def save(root, q):
    """Append to history. The caller runs compact_index.py to project it into the index."""
    _, hist = paths(root)
    with open(hist, "a", encoding="utf-8") as f:
        f.write(json.dumps(q, ensure_ascii=False) + "\n")


def order(entries):
    """Queue order: shortest note first, so a batch is predictable in cost and the two
    outliers do not land in the same session as thirty small ones."""
    notes = [e for e in entries if str(e.get("id", "")).startswith("augment_wiki/")
             and e.get("type") in TYPES]
    def size(e):
        try:
            return os.path.getsize(e["id"])
        except OSError:
            return 0
    return [e["id"] for e in sorted(notes, key=lambda e: (size(e), e["id"]))]


def main():
    root = "."
    args = sys.argv[1:]
    if args and not args[0].startswith("-") and args[0] not in (
            "init", "status", "next", "done", "batch", "close"):
        root, args = args[0], args[1:]
    cmd = args[0] if args else "status"
    rest = args[1:]
    entries, q = load(root)

    if cmd == "init":
        if q and q.get("pending"):
            sys.exit(f"error: a restyle queue is already open with {len(q['pending'])} pending")
        batch = 40
        if "--batch" in rest:
            batch = int(rest[rest.index("--batch") + 1])
        ids = order(entries)
        q = {"id": "restyle", "kind": "restyle", "declared": TODAY, "batch": batch,
             "pending": ids, "done": [],
             "note": "Batched rebuild of every content note under the current WRITE_FLOW "
                     "(PROCESS, RESTYLE mode)."}
        save(root, q)
        print(f"restyle queue opened: {len(ids)} notes, batch {batch}")
        return

    if not q:
        if cmd == "status":
            print("restyle: dormant, no queue open (init one when the writing rules change)")
            return
        sys.exit("error: no restyle queue; run `init` first")
    pending, done, batch = q.get("pending", []), q.get("done", []), q.get("batch", 40)

    if cmd == "status":
        print(f"restyle: {len(done)} done, {len(pending)} pending, batch {batch}")
        if pending:
            print(f"  next batch ({min(batch, len(pending))}):")
            for i in pending[:batch]:
                print("   ", i)
        else:
            print("  queue empty: the pass is complete")
        return

    if cmd == "next":
        for i in pending[:batch]:
            print(i)
        return

    if cmd == "batch":
        q = {**q, "batch": int(rest[0]), "declared": TODAY}
        save(root, q)
        print(f"batch size set to {rest[0]}")
        return

    if cmd == "close":
        # A finished queue is retired outright, not collapsed to a smaller entry.
        # Which notes were rebuilt and what each rebuild found is already in the
        # `restyle_run` markers and the per-note history lines, so anything kept
        # here duplicates the ledger inside the projection every script reads, and
        # a summary left behind goes stale on its own: the closed entry written on
        # 2026-08-15 still named an operation file that had been retired the same
        # day. The tombstone drops the id from the index at the next compaction
        # while the ledger keeps every line it ever had (CONTRACT §9), and `init`
        # reopens cleanly the next time the writing rules change.
        if pending:
            sys.exit(f"error: {len(pending)} notes still pending; close is for a finished queue")
        save(root, {"id": "restyle", "kind": "restyle", "retired": True,
                    "closed": TODAY, "completed": len(done)})
        print(f"restyle queue closed and retired: {len(done)} notes completed, "
              f"the record stays in history.jsonl")
        return

    if cmd == "done":
        if not rest:
            sys.exit("usage: restyle_queue.py . done <id> [<id>…]")
        unknown = [i for i in rest if i not in pending]
        if unknown:
            sys.exit(f"error: not pending (already done, or a typo): {unknown}")
        q = {**q, "pending": [i for i in pending if i not in rest],
             "done": done + list(rest), "declared": TODAY}
        save(root, q)
        print(f"marked done: {len(rest)}; {len(q['pending'])} pending")
        return

    sys.exit(f"error: unknown command {cmd!r}")


if __name__ == "__main__":
    main()
