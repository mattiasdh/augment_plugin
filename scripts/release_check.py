#!/usr/bin/env python3
"""Release check for a published document (WRITE_FLOW §4).

Runs the mechanical half of pass 3 with no model call, on one file at a time.
A published document is anything the vault does not regenerate, which includes
assisted source notes: nothing rebuilds them, so a defect in one is permanent
and a gate before emission is the only place it gets caught.

Three checks, all deterministic:

  1. Footnotes. Every `[^n]` used is defined at the foot, and every definition is
     used. An undefined reference renders as literal text in Obsidian and in any
     export; an unused definition is usually the trace of a cut paragraph whose
     citation stayed behind.
  2. Wikilinks resolve. `[[target]]` matched against every file basename in the
     vault, with and without extension, since Obsidian resolves by basename
     regardless of folder. A dead link in a deliverable is worse than in a wiki
     note: nothing rebuilds it, so it stays dead.
  3. Typography swept, the same rules `conformance.py` enforces on the wiki
     (WRITE_FLOW §2), re-run here because a source note is outside the set
     `conformance.py` walks and would otherwise never be checked.

Not checked, because a script cannot: grammar, per-language punctuation
conventions, whether numbers and dates hold one convention, whether acronyms are
expanded once. Those stay a reading job, and so does everything in §3.

Exit 1 on any finding so a caller can gate on it. The frontmatter and the `[!ai]`
callout are skipped for the typography pass: they are metadata about the text
rather than the text (WRITE_FLOW §0), and a provenance line legitimately carries
punctuation the body may not.

Usage:
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/release_check.py" <file> [<file> ...]
"""
import glob
import os
import re
import sys

VAULT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

FOOTNOTE_DEF = re.compile(r"(?m)^\[\^([^\]]+)\]:")
FOOTNOTE_USE = re.compile(r"\[\^([^\]]+)\](?!:)")
WIKILINK = re.compile(r"\[\[([^\]|#]+)")
EM_DASH = re.compile(r"[—]")
MIDDLE_DOT = re.compile(r"[·•]")


def vault_basenames():
    """Every file in the vault, by basename with and without extension.

    Obsidian resolves `[[target]]` by basename wherever the file sits, so the
    folder is irrelevant to whether a link works and must be irrelevant here too.
    """
    names = set()
    for f in glob.glob(os.path.join(VAULT, "**", "*"), recursive=True):
        if os.path.isfile(f):
            base = os.path.basename(f)
            names.add(base)
            names.add(os.path.splitext(base)[0])
    return names


def body_lines(text):
    """Lines of the document proper: frontmatter and callout stripped.

    Both are metadata about the text rather than the text (WRITE_FLOW §0), and the
    `[!ai]` block records provenance in a register the body's rules do not govern.
    """
    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                lines = lines[i + 1:]
                break
    return [l for l in lines if not l.lstrip().startswith(">")]


def check(path, names):
    findings = []
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    defined = set(FOOTNOTE_DEF.findall(text))
    used = set(FOOTNOTE_USE.findall(text))
    for n in sorted(defined - used):
        findings.append(f"footnote [^{n}] defined but never used")
    for n in sorted(used - defined):
        findings.append(f"footnote [^{n}] used but never defined")

    for target in sorted({t.strip() for t in WIKILINK.findall(text)}):
        # `[[source]]` is this vault's Type line on every source note, a
        # convention rather than a link to a file that exists.
        if target == "source":
            continue
        if target not in names:
            findings.append(f"wikilink [[{target}]] resolves to no file")

    for i, line in enumerate(body_lines(text), 1):
        if EM_DASH.search(line):
            findings.append(f"line {i}: em dash (WRITE_FLOW §2)")
        if MIDDLE_DOT.search(line):
            findings.append(f"line {i}: middle dot (WRITE_FLOW §2)")

    return findings


def main():
    if len(sys.argv) < 2:
        print(__doc__.strip().splitlines()[-1].strip())
        return 2

    names = vault_basenames()
    total = 0
    for path in sys.argv[1:]:
        if not os.path.exists(path):
            print(f"RELEASE CHECK: no such file: {path}")
            total += 1
            continue
        findings = check(path, names)
        rel = os.path.relpath(path, VAULT)
        if findings:
            print(f"RELEASE CHECK: {len(findings)} finding(s) in {rel}")
            for f in findings:
                print(f"  ! {f}")
            total += len(findings)
        else:
            print(f"RELEASE CHECK: clean, {rel}")

    if total:
        print(f"\n{total} finding(s). Not ready to emit.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
