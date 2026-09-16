#!/usr/bin/env python3
"""Regenerate augment_wiki/view/sources.md, the index into the source layer (CONTRACT §12).

Groups every processed source by its project or library context, marks whether a
wiki note cites it (● linked / ○ processed but unlinked), and links each context
to the wiki notes its sources produced. This makes the wiki a point of entry
into the sources, including the processed-but-unlinked ones (meeting notes,
how-to files) that no concept was extracted from and that a detailed question
still needs. Generated in DREAM phase 7 from index.jsonl.
"""
import json, os, sys
from _gen_util import display_path, write_if_changed, fm_block, stamp, load_config
from collections import defaultdict

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
IDX = os.path.join(ROOT, "augment_wiki/index.jsonl")
STAMP = stamp()

def ctx(p, rules, cfg):
    """Stable, anchor-safe context name (no parentheses): note headings double as
    link anchors, so project/concept notes back-link to their section with
    `further_sources: "[[sources#<context>]]"`, and a context name that moved would
    break every one of those pointers.

    Grouping comes from `config.yaml`'s optional `source_contexts`, so
    the view is not wired to one vault's folder names. Each rule is
    `{"path": ..., "group_by": "child", "prefix": true|false}`: `child` groups by
    the folder one level inside `path` (a file sitting directly in `path` becomes
    its "loose files" or "root" group), and `prefix` renders the parent alongside
    the child. With no rule matching, the context is the top-level folder, which
    is the whole behaviour for a vault that declares nothing."""
    p = display_path(p, cfg)
    rules = [dict(r, path=display_path(r.get("path", ""), cfg)) for r in rules]
    best = None
    for r in rules:
        d = r.get("path", "")
        if (p == d or p.startswith(d + "/")) and (best is None or len(d) > len(best.get("path", ""))):
            best = r
    if best is None or best.get("group_by") != "child":
        return p.split("/")[0]
    d, pre = best["path"], best.get("prefix", False)
    rest = p[len(d) + 1:].split("/")
    if len(rest) > 1:
        return f"{d} / {rest[0]}" if pre else rest[0]
    return f"{d} / root" if pre else f"{d} loose files"

def link(path):  # exact by full path, collision-proof, aliased to the basename
    noext = path[:-3] if path.endswith(".md") else path
    return f"[[{noext}|{os.path.basename(noext)}]]"

def base(i):
    return os.path.splitext(os.path.basename(i))[0]

def main():
    idx = [json.loads(l) for l in open(IDX, encoding="utf-8") if l.strip()]
    # A source id is a repo-relative path (CONTRACT §9), so it ends in `.md`. Naming
    # the bookkeeping entries to exclude instead let `config` and `restyle` through as
    # source contexts, and counted them among the sources; testing the shape holds for
    # any bookkeeping entry added later.
    #
    # `#excluded` sources are omitted outright, never listed as ○ "processed,
    # unlinked": that caption is also factually wrong for them (declared out is not
    # processed), and CONTRACT §5's confidentiality escape hatch exists precisely so
    # a source never surfaces, which a clickable wikilink in a generated index
    # defeats regardless of caption. Found 2026-08-26 when a NAS-credentials file
    # excluded the day before turned up here as a plain link.
    srcs = [e for e in idx if str(e.get("id", "")).endswith(".md")
            and not str(e.get("id", "")).startswith("augment_wiki/")
            and e.get("status") != "excluded"]
    cfg = load_config(ROOT)
    rules = cfg.get("source_contexts") or []
    groups = defaultdict(list)
    for e in srcs:
        groups[ctx(e["id"], rules, cfg)].append(e)

    out = fm_block(generated_by='augment/gen_sources.py', generated_at=STAMP, type='"[[hub]]"', status='"#current"') + ["# sources", "",
           "Index into the source layer, grouped by project or library context. "
           "The wiki is a point of entry into the sources, not a wall around them: "
           "a general question is usually answered from the notes, a detailed one "
           "by opening the sources here, including the processed-but-unlinked ones. "
           "Each context links to the wiki notes it produced. Legend: ● cited by a "
           "wiki note, ○ processed but unlinked. Generated from `index.jsonl`. Do "
           "not edit by hand.", ""]
    total_u = 0
    for g in sorted(groups):
        members = sorted(groups[g], key=lambda e: e["id"])
        notes = sorted({n for e in members for n in e.get("produced", [])})
        out.append(f"## {g}")  # clean heading = stable link anchor
        if notes:
            out.append("Wiki notes: " + ", ".join(f"[[{base(n)}]]" for n in notes))
        for e in members:
            if e.get("produced"):
                out.append(f"- ● {link(e['id'])}")
            else:
                out.append(f"- ○ {link(e['id'])} (processed, unlinked)")
                total_u += 1
        out.append("")
    write_if_changed(os.path.join(ROOT, "augment_wiki/view/sources.md"), "\n".join(out))
    print(f"regenerated sources: {len(srcs)} sources, {total_u} processed-unlinked, {len(groups)} contexts")

if __name__ == "__main__":
    main()
