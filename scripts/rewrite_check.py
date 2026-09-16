#!/usr/bin/env python3
"""Measure how much of a claimed rewrite is actually new text (WRITE_FLOW §2).

A rewrite and an edit produce output that looks alike, so the label on a pass is
unverifiable from the result. This measures it: the share of the new version's
sentences that are carried over byte-identical from the old one.

The failure this exists for is documented rather than hypothetical. On this
vault, two consecutive passes over the same source note were labelled
"rewritten from the sources" and carried 85% and 80% of their sentences over
unchanged, each asserting in its own callout that a read-back against the
sources had found nothing wrong. A defect introduced three passes earlier
survived all of them, because a sentence that is never rewritten is never
re-read against what it cites.

Carryover is not a defect on its own. A sentence that is already right should
survive a rewrite, and an edit pass is a legitimate operation. The finding is a
mismatch between the number and the label: above the threshold, either the pass
was an edit and should say so, or it claimed to re-derive text it in fact
inherited.

**What this cannot see, and it is the worse case.** The comparison is
byte-identical, so it catches an edit that left sentences alone and is blind to
one that swapped every content word for a synonym while carrying the claim
across unchanged. Measured on the section that motivated `--section`, a pass
whose every sentence was synonym-cycled from the previous version scores 0% and
passes clean. A low number therefore means "not copied verbatim", never "derived
from the sources". The guard against disguised carryover is the drafting
sequence in WRITE_FLOW §2 (brief, close the target, draft from sources, then
splice) and the counterfeit-cleft and synonym-cycling entries in §3; this script
does not substitute for either.

Sentences are compared after stripping frontmatter, callouts, tables, footnote
definitions and headings, since apparatus is meant to survive (WRITE_FLOW §3)
and would otherwise inflate the number it is not evidence about.

**Scope the check to what was claimed.** A whole-file number on a pass that
rewrote one section is noise, and noise gets explained away: a section rewrite
here measured 77% across the file and the number was dismissed, correctly on
its own terms, as expected since most of the file was out of scope. Measured on
the section actually claimed, it would have been high and unarguable. Pass
`--section` with the heading text whenever the pass rewrote a section rather
than the document.

Usage:
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rewrite_check.py" <file> [<old-rev>]
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rewrite_check.py" <file> --section "4.2"

`old-rev` defaults to HEAD, so the common case is a working-tree rewrite checked
against the last commit. `--section` matches a heading by substring, case
insensitively, and compares only that heading's own content, stopping at the
next heading of the same or a higher level. Exit 1 when carryover is at or above
the threshold.
"""
import re
import subprocess
import sys

THRESHOLD = 50  # percent; above this, "rewrite" is the wrong word for the pass
MIN_LEN = 40    # ignore fragments; they carry no sentence structure to compare


def slice_section(text, needle):
    """The named heading's own content, to the next heading of the same or higher level.

    Returns None when the heading is not found, which the caller reports rather
    than silently measuring the whole file: a typo in the section name would
    otherwise produce a number that answers a different question.
    """
    lines = text.splitlines()
    needle = needle.lower()
    start = level = None
    for i, l in enumerate(lines):
        m = re.match(r"^(#+)\s+(.*)$", l)
        if not m:
            continue
        if start is None:
            if needle in m.group(2).lower():
                start, level = i, len(m.group(1))
            continue
        if len(m.group(1)) <= level:
            return "\n".join(lines[start + 1:i])
    if start is None:
        return None
    return "\n".join(lines[start + 1:])


def body_sentences(text):
    """Prose sentences only: apparatus stripped, since it is meant to survive."""
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                lines = lines[i + 1:]
                break
    keep = [l for l in lines
            if l.strip() and not l.lstrip().startswith((">", "|", "[^", "#", "---"))]
    parts = re.split(r"(?<=[.!?])\s+", " ".join(keep))
    return [p.strip() for p in parts if len(p.strip()) >= MIN_LEN]


def at_rev(path, rev):
    r = subprocess.run(["git", "show", f"{rev}:{path}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return r.stdout


def main():
    args = [a for a in sys.argv[1:]]
    section = None
    if "--section" in args:
        i = args.index("--section")
        if i + 1 >= len(args):
            print("usage: rewrite_check.py <file> [<old-rev>] [--section <heading>]")
            return 2
        section = args[i + 1]
        del args[i:i + 2]
    if not args:
        print("usage: rewrite_check.py <file> [<old-rev>] [--section <heading>]")
        return 2
    path = args[0]
    rev = args[1] if len(args) > 1 else "HEAD"

    old = at_rev(path, rev)
    if old is None:
        print(f"REWRITE CHECK: {path} does not exist at {rev}; nothing to compare")
        return 0
    try:
        new = open(path, encoding="utf-8").read()
    except OSError as e:
        print(f"REWRITE CHECK: cannot read {path}: {e}")
        return 2

    scope = path
    if section is not None:
        old_s, new_s = slice_section(old, section), slice_section(new, section)
        missing = [n for n, v in (("old", old_s), ("new", new_s)) if v is None]
        if missing:
            print(f"REWRITE CHECK: no heading matching {section!r} in the "
                  f"{' and '.join(missing)} version of {path}")
            return 2
        old, new = old_s, new_s
        scope = f"{path} §{section}"

    a, b = body_sentences(old), body_sentences(new)
    if not b:
        print(f"REWRITE CHECK: no prose sentences found in {scope}")
        return 0

    carried = sorted(set(a) & set(b), key=len, reverse=True)
    pct = round(100 * len(carried) / len(b))

    print(f"REWRITE CHECK: {scope}")
    print(f"  against {rev}: {len(a)} sentences before, {len(b)} after, "
          f"{len(carried)} carried over byte-identical ({pct}%)")

    if pct >= THRESHOLD:
        print(f"\n  ! {pct}% carryover. This is an edit, not a rewrite from the sources.")
        print("    Either relabel the pass, or draft the text before consulting the")
        print("    old version and diff afterwards (WRITE_FLOW §2). Longest carried:")
        for s in carried[:5]:
            print(f"      - {s[:100]}{'…' if len(s) > 100 else ''}")
        return 1

    print(f"  carryover below the {THRESHOLD}% threshold; consistent with a rewrite.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
