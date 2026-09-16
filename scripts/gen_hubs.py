#!/usr/bin/env python3
"""Regenerate the hub notes in augment_wiki/hub/ from index.jsonl (CONTRACT §11).

One hub per Type and per Kind, each an alphabetic index (by title, articles
ignored) of its members, plus hub.md indexing the hubs. Overwrites wholesale.
Run from the vault root after index compaction (DREAM phase 7).
"""
import json, os, re, sys
from collections import defaultdict
from _gen_util import write_if_changed, fm_block, stamp

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
IDX = os.path.join(ROOT, "augment_wiki/index.jsonl")
STAMP = stamp()

KIND_DESC = {
    "principle": "All principle concepts.", "method": "All method concepts.",
    "model": "All model concepts.", "metric": "All metric concepts.",
    "standard": "All standard concepts.", "claim": "All claim concepts.",
    "procedure": "All procedure concepts.",
    "organisation": "All organisation entities.", "product": "All product entities.",
    "tool": "All tool entities.", "project": "All project entities.",
    "place": "All place entities.", "person": "All person entities.",
}

def base(e): return os.path.splitext(os.path.basename(e["id"]))[0]
def sortkey(t): return re.sub(r"^(the|a|an)\s+", "", t.strip(), flags=re.I).lower()
def letter(t): return re.sub(r"^(the|a|an)\s+", "", t.strip(), flags=re.I)[0].upper()

def write_hub(name, desc, members):
    members = sorted(members, key=lambda e: sortkey(e["title"]))
    groups = defaultdict(list)
    for e in members:
        groups[letter(e["title"])].append(e)
    out = fm_block(generated_by='augment/gen_hubs.py', generated_at=STAMP, type='"[[hub]]"', status='"#current"') + ["# " + name, "",
           desc + " Generated from `index.jsonl`, alphabetically by title. Do not edit by hand.", ""]
    for L in sorted(groups):
        out.append("## " + L)
        for e in groups[L]:
            out.append(f"- [[{base(e)}]]: {e['title']}")
        out.append("")
    write_if_changed(os.path.join(ROOT, f"augment_wiki/hub/{name}.md"), "\n".join(out))

def main():
    idx = [json.loads(l) for l in open(IDX) if l.strip()]
    notes = [e for e in idx if str(e["id"]).startswith("augment_wiki/") and e.get("type") in ("concept", "entity", "tension", "theme")]
    write_hub("concept", "All concept notes.", [e for e in notes if e["type"] == "concept"])
    write_hub("entity", "All entity notes.", [e for e in notes if e["type"] == "entity"])
    tensions = [e for e in notes if e["type"] == "tension"]
    if tensions:
        write_hub("tension", "All tension notes.", tensions)
    themes = [e for e in notes if e["type"] == "theme"]
    if themes:
        write_hub("theme", "All theme notes (topical anchors, §3).", themes)
    types = ["concept", "entity"] + (["tension"] if tensions else []) + (["theme"] if themes else [])
    # Kind hubs come from concept/entity only; tension and theme notes carry no Kind.
    # Grouped by their owning Type as well, so hub.md can nest each Kind under it.
    kinds = defaultdict(list)
    kinds_by_type = defaultdict(set)
    for e in notes:
        if e.get("kind"):
            kinds[e["kind"]].append(e)
            kinds_by_type[e["type"]].add(e["kind"])
    for k, mem in kinds.items():
        write_hub(k, KIND_DESC.get(k, f"All {k} notes."), mem)
    # Views (CONTRACT §12) are generated indexes too, living in augment_wiki/view/; list any that exist.
    views = [v for v in ("relations", "timeline", "sources")
             if os.path.exists(os.path.join(ROOT, f"augment_wiki/view/{v}.md"))]
    out = fm_block(generated_by='augment/gen_hubs.py', generated_at=STAMP, type='"[[hub]]"', status='"#current"') + ["# hub", "",
           "Index of the wiki hub notes (one per Type and per Kind) and views (§12). Generated from `index.jsonl`.", ""]
    for t in types:
        out.append(f"## [[{t}]]")
        for k in sorted(kinds_by_type[t]):
            out.append(f"- [[{k}]]")
        out.append("")
    if views:
        out += ["## Views", ""] + [f"- [[{v}]]" for v in views] + [""]
    write_if_changed(os.path.join(ROOT, "augment_wiki/hub/hub.md"), "\n".join(out))
    print(f"regenerated {len(types) + len(kinds) + 1} hubs, {len(views)} views listed")

if __name__ == "__main__":
    main()
