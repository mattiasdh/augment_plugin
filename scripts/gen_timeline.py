#!/usr/bin/env python3
"""Regenerate augment_wiki/view/timeline.md, the per-project decision chronology (CONTRACT §12).

Aggregates the `## Decisions` block of every project entity (index kind ==
"project") into one dated view, grouped by project and ordered in time within
each. Reads the note files because decision lines live in bodies, not the index.
Always writes the file, even when empty, so `[[timeline]]` never dangles.
Run from the vault root in DREAM phase 7, after index compaction.
"""
import json, os, re, sys
from _gen_util import write_if_changed, fm_block, stamp

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
IDX = os.path.join(ROOT, "augment_wiki/index.jsonl")
STAMP = stamp()

DECISION = re.compile(r"^-\s+(\d{4}-\d{2}-\d{2})\b")

def sortkey(t): return re.sub(r"^(the|a|an)\s+", "", t.strip(), flags=re.I).lower()

def decisions_of(path):
    """Return (date, rawline) for each dated line under a `## Decisions` header."""
    try:
        lines = open(os.path.join(ROOT, path), encoding="utf-8").read().splitlines()
    except FileNotFoundError:
        return []
    out, in_block = [], False
    for ln in lines:
        if ln.strip() == "## Decisions":
            in_block = True
            continue
        if in_block and ln.startswith("## "):
            break
        if in_block:
            m = DECISION.match(ln.strip())
            if m:
                out.append((m.group(1), ln.strip()))
    return out

def main():
    idx = [json.loads(l) for l in open(IDX, encoding="utf-8") if l.strip()]
    projects = [e for e in idx
                if str(e.get("id", "")).startswith("augment_wiki/")
                and e.get("type") == "entity" and e.get("kind") == "project"]
    projects.sort(key=lambda e: sortkey(e.get("title", e["id"])))

    body, total = [], 0
    for e in projects:
        rows = sorted(decisions_of(e["id"]), key=lambda r: r[0])
        if not rows:
            continue
        total += len(rows)
        base = os.path.splitext(os.path.basename(e["id"]))[0]
        body.append(f"## [[{base}]] {e.get('title', base)}")
        body += [row for _, row in rows]
        body.append("")

    head = fm_block(generated_by='augment/gen_timeline.py', generated_at=STAMP, type='"[[hub]]"', status='"#current"') + ["# timeline", "",
            "Per-project decision chronology, grouped by project and ordered in "
            "time. Generated from the `## Decisions` blocks of project entities "
            "(CONTRACT §12). Do not edit by hand.", ""]
    if not body:
        body = ["No project decisions harvested yet.", ""]
    write_if_changed(os.path.join(ROOT, "augment_wiki/view/timeline.md"), "\n".join(head + body))
    print(f"regenerated timeline: {total} decisions across "
          f"{sum(1 for e in projects if decisions_of(e['id']))} projects")

if __name__ == "__main__":
    main()
