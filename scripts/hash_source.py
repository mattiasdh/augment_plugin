#!/usr/bin/env python3
"""Canonical source content hash (reference/scope-and-index.md, Hashing).

The hash covers the body and nothing else: sha256 over the file with its
frontmatter removed, first 8 hex chars. Removed, in order:

  1. a leading fenced frontmatter block, `---` through the next `---` or `...`
     line (an unclosed fence is not frontmatter, and hashes as content);
  2. any leading bare declaration lines, `augment:`, `wiki:`, `created:`,
     `updated:`, `assisted_by:` or the old `Status:`, the pre-frontmatter form a
     file with no block may still carry;
  3. any blank lines left at the top.

So everything written as metadata is outside the hash: a status tag, a
backlink line, a changed `tags:` or `title:`, and whether the block is fenced
at all. A file converted from the bare form to a fenced block hashes
identically, which is what lets a metadata write add a block where none
existed. Until v2026-09-24 only five named lines were excluded, so a status
write had to be a byte-preserving line insert and a new fence shifted the
hash; `migrate_hash_v2.py` re-stamps a vault from that rule to this one.

The body is hashed byte for byte, line endings included, so a CRLF->LF
normalisation or a reflow of the text changes the hash exactly as an edit
would. This is the one canonical implementation; a reimplementation on
Python's str.splitlines (which also splits on \\r, \\x0b, \\x0c and Unicode
separators) silently disagrees and raises false staleness.
"""
import hashlib, re, sys

_DECL = re.compile(rb"^(Status|augment|wiki|created|updated|assisted_by):")
_BOM = b"\xef\xbb\xbf"


def body_lines(raw):
    """The file's lines after the frontmatter, as bytes without their \\n."""
    segments = raw.split(b"\n")
    if raw.endswith(b"\n"):
        segments = segments[:-1]           # trailing \n yields no extra line
    i = 0
    if segments and segments[0].lstrip(_BOM).rstrip(b"\r") == b"---":
        for j in range(1, len(segments)):
            if segments[j].rstrip(b"\r") in (b"---", b"..."):
                i = j + 1
                break
    while i < len(segments) and _DECL.match(segments[i].lstrip(_BOM)):
        i += 1
    while i < len(segments) and not segments[i].strip(b" \t\r"):
        i += 1
    return segments[i:]


def content_hash_bytes(raw):
    body = b"".join(s + b"\n" for s in body_lines(raw))
    return hashlib.sha256(body).hexdigest()[:8]


def content_hash(path):
    with open(path, "rb") as f:
        return content_hash_bytes(f.read())


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(content_hash(p), p)
