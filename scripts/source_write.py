#!/usr/bin/env python3
"""The system's writes into a person's source note, and nothing else.

A source is the person's authorship: its body is never rewritten, reflowed or
re-encoded. The system writes into it in exactly two ways, and both live here so
that no session improvises them inline and no surface without a shell has to
reproduce file bytes through a model:

  set      one system key in the frontmatter: `augment:` (the status),
           `created:`, `updated:` or `assisted_by:`. Metadata, outside the v2
           hash, so the content hash must come out unchanged, and the write is
           refused if it would not. A bare-form file (declaration lines, no
           `---` block) is given a block; a file with no frontmatter at all gets
           one. The person's own keys are never touched or reordered.

  callout  a `> [!ai]` or `> [!note]` callout (WRITE comment mode), placed after
           the `# Title` line or at the head of a named section. Body content, so
           the hash moves, which is the point; the check here is the opposite
           one: removing the inserted lines must give back the original body
           byte for byte. Also stamps `updated:`.

Every write keeps the file's newline convention, matching the line it is
written beside. Nothing is written with --dry-run; the result is printed.

    python3 source_write.py <vault> set <path> <key> <value> [--dry-run]
    python3 source_write.py <vault> callout <path> --kind ai|note --actor A
            --date YYYY-MM-DD --text "one paragraph" [--heading "## Section"] [--dry-run]

<path> is relative to <vault>. Exit 0 on a write (or a no-op), 1 on a refusal.
"""
import argparse, datetime, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hash_source import content_hash_bytes

KEYS = ("augment", "created", "updated", "assisted_by")
_DECL = re.compile(rb"^(Status|augment|wiki|created|updated|assisted_by):")
_BOM = b"\xef\xbb\xbf"


def _split(raw):
    trailing = raw.endswith(b"\n")
    lines = raw.split(b"\n")
    if trailing:
        lines = lines[:-1]
    return lines, trailing


def _join(lines, trailing):
    return b"\n".join(lines) + (b"\n" if trailing else b"")


def _fence(lines):
    """(open, close) indices of a leading fenced block, or None."""
    if lines and lines[0].lstrip(_BOM).rstrip(b"\r") == b"---":
        for j in range(1, len(lines)):
            if lines[j].rstrip(b"\r") in (b"---", b"..."):
                return 0, j
    return None


def _value(key, value):
    if key == "augment":
        return f'augment: "{value}"'.encode("utf-8")
    return f"{key}: {value}".encode("utf-8")


def set_key(raw, key, value):
    """`raw` with system key `key` set to `value`; the body is left as it was."""
    lines, trailing = _split(raw)
    pat = re.compile(rb"^" + key.encode() + rb":")
    fence = _fence(lines)
    if fence:
        _, close = fence
        block = lines[1:close]
        near = next((l for l in block if _DECL.match(l)), lines[0])
        cr = b"\r" if near.endswith(b"\r") else b""
        new = _value(key, value) + cr
        k = next((i for i, l in enumerate(block) if pat.match(l)), None)
        if k is not None:
            if block[k] == new:
                return raw
            block[k] = new
        elif key == "augment":
            block.insert(0, new)
        else:
            last = max((i for i, l in enumerate(block) if _DECL.match(l)), default=len(block) - 1)
            block.insert(last + 1, new)
        return _join(lines[:1] + block + lines[close:], trailing)

    lead = 0
    while lead < len(lines) and _DECL.match(lines[lead].lstrip(_BOM)):
        lead += 1
    decl = lines[:lead]
    first = decl[0] if decl else (lines[0] if lines else b"")
    cr = b"\r" if first.endswith(b"\r") else b""
    new = _value(key, value) + cr
    k = next((i for i, l in enumerate(decl) if pat.match(l.lstrip(_BOM))), None)
    if k is not None:
        decl[k] = new
    elif key == "augment":
        decl.insert(0, new)
    else:
        decl.append(new)
    body = lines[lead:]
    if not trailing and not body and not lines:
        trailing = True
    return _join([b"---" + cr] + decl + [b"---" + cr] + body, trailing)


def insert_callout(raw, kind, actor, date, text, heading=None):
    """(new raw, inserted line indices) with the callout placed, or raises."""
    if "\n" in text or "\r" in text:
        raise ValueError("callout text must be one paragraph on one line")
    lines, trailing = _split(raw)
    fence = _fence(lines)
    start = fence[1] + 1 if fence else 0
    if heading:
        target = heading.strip().encode("utf-8")
        at = next((i for i in range(start, len(lines)) if lines[i].rstrip(b"\r").strip() == target), None)
        if at is None:
            raise ValueError(f"heading not found: {heading}")
    else:
        at = next((i for i in range(start, len(lines)) if lines[i].startswith(b"# ")), None)
        if at is None:  # no title: the callout opens the body
            at = start - 1
    near = lines[at] if 0 <= at < len(lines) else (lines[start] if start < len(lines) else b"")
    cr = b"\r" if near.endswith(b"\r") else b""
    block = [b"" + cr,
             f"> [!{kind}] {actor}, {date}".encode("utf-8") + cr,
             f"> {text}".encode("utf-8") + cr]
    rest = lines[at + 1:]
    if rest and rest[0].strip(b" \t\r"):
        block.append(b"" + cr)
    elif not rest:
        pass
    new = lines[:at + 1] + block + rest
    return _join(new, trailing), list(range(at + 1, at + 1 + len(block)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("vault")
    sub = ap.add_subparsers(dest="mode", required=True)
    s = sub.add_parser("set")
    s.add_argument("path"); s.add_argument("key", choices=KEYS); s.add_argument("value")
    s.add_argument("--dry-run", action="store_true")
    c = sub.add_parser("callout")
    c.add_argument("path")
    c.add_argument("--kind", choices=("ai", "note"), required=True)
    c.add_argument("--actor", required=True)
    c.add_argument("--date", required=True)
    c.add_argument("--text", required=True)
    c.add_argument("--heading")
    c.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    rel = os.path.normpath(a.path)
    if rel.startswith("..") or os.path.isabs(rel) or rel.startswith("augment_wiki"):
        print(f"REFUSED: {a.path} is not a source path inside the vault"); sys.exit(1)
    p = os.path.join(a.vault, rel)
    if not os.path.isfile(p):
        print(f"REFUSED: no such file {rel}"); sys.exit(1)
    raw = open(p, "rb").read()

    if a.mode == "set":
        out = set_key(raw, a.key, a.value)
        if out == raw:
            print(f"unchanged: {rel} already has {a.key}"); return
        if content_hash_bytes(out) != content_hash_bytes(raw):
            print(f"REFUSED, write would move the content hash: {rel}"); sys.exit(1)
        verb = f"set {a.key}"
    else:
        try:
            out, added = insert_callout(raw, a.kind, a.actor, a.date, a.text, a.heading)
        except ValueError as e:
            print(f"REFUSED: {e}"); sys.exit(1)
        lines, trailing = _split(out)
        back = _join([l for i, l in enumerate(lines) if i not in set(added)], trailing)
        if back != raw:
            print(f"REFUSED, the insert would alter existing text: {rel}"); sys.exit(1)
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        out = set_key(out, "updated", stamp)
        verb = f"callout [!{a.kind}]"
    if a.dry_run:
        sys.stdout.write(out.decode("utf-8", "replace")); return
    with open(p, "wb") as f:
        f.write(out)
    print(f"{verb}: {rel} (hash {content_hash_bytes(out)})")


if __name__ == "__main__":
    main()
