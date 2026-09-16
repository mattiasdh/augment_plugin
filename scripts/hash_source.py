#!/usr/bin/env python3
"""Canonical source content hash (CONTRACT §9).

The content hash is sha256, first 8 hex chars, over the file with the three
declaration lines removed: any line beginning `augment:`, `created:`,
`updated:` or `assisted_by:` (and `Status:`, the pre-frontmatter form of `augment:`,
kept so a stray old-style file still hashes the same). Everything else counts, including line endings, so a CRLF->LF
normalisation or a reflow changes the hash exactly as an edit would.

This is the one canonical implementation. It reproduces every hash the vault
has ever stored; a reimplementation that diverges on trailing-newline or line
separator handling (e.g. Python str.splitlines, which splits on \\r, \\x0b,
\\x0c and Unicode separators too) will silently disagree and raise false
staleness. Equivalent shell form, kept identical on purpose:

    grep -vE '^(Status|augment|created|updated|assisted_by):' FILE | sha256sum | cut -c1-8
"""
import hashlib, re, sys

_DECL = re.compile(rb"^(Status|augment|created|updated|assisted_by):")

def content_hash(path):
    with open(path, "rb") as f:
        raw = f.read()
    segments = raw.split(b"\n")
    if raw.endswith(b"\n"):
        segments = segments[:-1]           # trailing \n yields no extra line
    kept = [s for s in segments if not _DECL.match(s)]
    body = b"".join(s + b"\n" for s in kept)  # grep newline-terminates each line
    return hashlib.sha256(body).hexdigest()[:8]

if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(content_hash(p), p)
