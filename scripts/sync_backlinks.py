#!/usr/bin/env python3
"""Keep each source's `wiki:` frontmatter line in step with the index.

A processed source that some wiki note cites carries, immediately under its
`augment:` line, the notes citing it:

    wiki: ["[[pace-layering]]", "[[shearing-layers-of-change]]"]

so the backlink is readable from inside the source, in any editor, without the
index. The index's `produced` list is the authority and this line its mirror,
the same relation the `#linked`/`#unlinked` tag already has to it. A source
nothing cites carries no line: `#unlinked` on the line above says so already.

Idempotent and mechanical: run it after compaction, and it adds, rewrites or
removes the line wherever the mirror disagrees. Only the frontmatter is ever
touched. A bare-form file (declaration lines with no `---` block) is given a
block when a line has to be written, which the v2 hash does not see; each
file's newline convention is kept. Every write is checked against the content
hash before and after, and a file whose hash would move is left untouched and
reported, since that would be a body edit, which this script must never make.
`#excluded` sources are never opened.

    python3 sync_backlinks.py <vault> [--dry-run]
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hash_source import content_hash_bytes

_DECL = re.compile(rb"^(Status|augment|wiki|created|updated|assisted_by):")
_WIKI = re.compile(rb"^wiki:")
_AUG = re.compile(rb"^augment:")


def slug(note_id):
    return os.path.splitext(os.path.basename(note_id))[0]


def wiki_line(produced):
    if not produced:
        return None
    items = ", ".join(f'"[[{s}]]"' for s in sorted({slug(p) for p in produced}))
    return f"wiki: [{items}]".encode("utf-8")


def rewrite(raw, desired):
    """`raw` with its `wiki:` line set to `desired` (None removes it)."""
    trailing = raw.endswith(b"\n")
    lines = raw.split(b"\n")
    if trailing:
        lines = lines[:-1]
    # Match the ending of the line written under, else the first line: files mixing
    # conventions inside one block exist, left by earlier edits, and the new line
    # should look like its neighbour rather than like the top of the file.
    anchor = next((l for l in lines[:40] if _AUG.match(l)), lines[0] if lines else b"")
    cr = b"\r" if anchor.endswith(b"\r") else b""
    new = desired + cr if desired is not None else None

    if lines and lines[0].rstrip(b"\r") == b"---":
        close = next((j for j in range(1, len(lines))
                      if lines[j].rstrip(b"\r") in (b"---", b"...")), None)
        if close is not None:
            block = lines[1:close]
            w = next((k for k, l in enumerate(block) if _WIKI.match(l)), None)
            if new is None:
                if w is not None:
                    del block[w]
            elif w is not None:
                block[w] = new
            else:
                a = next((k for k, l in enumerate(block) if _AUG.match(l)), None)
                block.insert(a + 1 if a is not None else len(block), new)
            lines = lines[:1] + block + lines[close:]
            return b"\n".join(lines) + (b"\n" if trailing else b"")

    lead = 0
    while lead < len(lines) and _DECL.match(lines[lead]):
        lead += 1
    decl = [l for l in lines[:lead] if not _WIKI.match(l)]
    if new is None:
        if len(decl) == lead:
            return raw
        lines = decl + lines[lead:]
        return b"\n".join(lines) + (b"\n" if trailing else b"")
    a = next((k for k, l in enumerate(decl) if _AUG.match(l)), None)
    decl.insert(a + 1 if a is not None else len(decl), new)
    lines = [b"---" + cr] + decl + [b"---" + cr] + lines[lead:]
    return b"\n".join(lines) + (b"\n" if trailing else b"")


def main():
    root = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "."
    dry = "--dry-run" in sys.argv
    idx = [json.loads(l) for l in open(os.path.join(root, "augment_wiki/index.jsonl"),
                                       encoding="utf-8") if l.strip()]
    counts = {"written": 0, "removed": 0, "unchanged": 0}
    refused = []
    for e in idx:
        i = str(e.get("id", ""))
        if i.startswith("augment_wiki/") or e.get("status") != "processed":
            continue
        p = os.path.join(root, i)
        if not os.path.exists(p):
            continue
        raw = open(p, "rb").read()
        desired = wiki_line(e.get("produced") or [])
        out = rewrite(raw, desired)
        if out == raw:
            counts["unchanged"] += 1
            continue
        if content_hash_bytes(out) != content_hash_bytes(raw):
            refused.append(i)
            continue
        counts["removed" if desired is None else "written"] += 1
        if not dry:
            with open(p, "wb") as f:
                f.write(out)
    print(f"backlinks: {counts['written']} written, {counts['removed']} removed, "
          f"{counts['unchanged']} unchanged" + (" (dry run)" if dry else ""))
    for r in refused:
        print(f"  REFUSED, write would move the content hash: {r}")
    sys.exit(1 if refused else 0)


if __name__ == "__main__":
    main()
