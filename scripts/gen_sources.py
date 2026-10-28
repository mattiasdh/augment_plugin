#!/usr/bin/env python3
"""Regenerate augment_wiki/view/sources.md, the index into the source layer (CONTRACT §12).

Groups every processed source by its project or library context, marks whether a
wiki note cites it (● linked / ○ processed but unlinked), and links each context
to the wiki notes its sources produced. This makes the wiki a point of entry
into the sources, including the processed-but-unlinked ones (meeting notes,
how-to files) that no concept was extracted from and that a detailed question
still needs. Generated in DREAM phase 7 from index.jsonl.
"""
import _cli
import json, os, sys
from _gen_util import display_path, write_if_changed, fm_block, stamp, load_config, context_of
from collections import defaultdict

ROOT = _cli.vault_arg()
IDX = os.path.join(ROOT, "augment_wiki/index.jsonl")
STAMP = stamp()

ctx = context_of

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
