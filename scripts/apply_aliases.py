#!/usr/bin/env python3
"""Write a wiki note's `aliases:`, the other names it is searched by (reference/note-shape.md).

The wiki is monolingual while the sources are not, so a note titled in English is
missed by a search in the language its own sources use. `aliases:` carries two to
four such names, Obsidian's native key, which Obsidian search, link completion
and the connector's `vault_search` all read.

**An alias must appear in one of the note's own sources.** That is what keeps it
a name and not an invention: the term the Dutch or French source actually uses,
never a translation the model supplies. The check is mechanical, case-, accent-
and whitespace-insensitive, against the files listed in the note's index entry
(`compiled_from`); an alias no source carries is refused and nothing is written.
A note with no recorded sources (a theme, a hub) takes no aliases.

Replacing the list is the write: pass the full set the note should carry. Plain
strings only, never wikilinks, at most four, none equal to the title or the slug.
The frontmatter alone changes, with `generated.at` bumped, and with `--reason` the
change reaches the ledger like any other write (`--auto --run <id>` for the
nightly cycle's unattended backfill, so `undo_run.py` can lift a night back out).

    python3 apply_aliases.py <vault> <slug> "alias one" "alias two" --reason "..." [--auto --run <id>]
    python3 apply_aliases.py <vault> --from-file batch.json --reason "..." [--auto --run <id>]
            (batch.json maps slug to a list of aliases)
    python3 apply_aliases.py <vault> <slug> ... --dry-run   # check and state, write nothing
"""
import argparse, json, os, re, subprocess, sys, unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gen_util import split_note, stamp, source_path
from apply_keywords import ledger_entry, locate, bump_stamp, keywords_span

MAX_ALIASES, MAX_LEN = 4, 60


def fold(text):
    """Lower case, accents dropped, whitespace collapsed: the form both sides are compared in."""
    t = unicodedata.normalize("NFKD", str(text))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", t).strip()


def index_entry(root, rel):
    p = os.path.join(root, "augment_wiki/index.jsonl")
    found = None
    for line in open(p, encoding="utf-8"):
        if line.strip():
            d = json.loads(line)
            if d.get("id") == rel:
                found = d
    return found or {}


def source_texts(root, entry):
    out = []
    for c in entry.get("compiled_from") or []:
        sid = c.get("source") if isinstance(c, dict) else c
        try:
            out.append(fold(open(source_path(root, sid), encoding="utf-8", errors="replace").read()))
        except (OSError, TypeError):
            continue
    return out


def check(root, slug, aliases):
    """Resolve the note and validate its aliases. Returns (path, errors)."""
    path = locate(root, slug)
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    fm, body = split_note(open(path, encoding="utf-8").read())
    title = next((l[2:].strip() for l in body.splitlines() if l.startswith("# ")), "")
    errors = []
    if len(aliases) > MAX_ALIASES:
        errors.append(f"{len(aliases)} aliases; {MAX_ALIASES} at most")
    texts = source_texts(root, index_entry(root, rel))
    if aliases and not texts:
        errors.append("the note has no readable sources in its index entry, so no alias can be checked")
    seen = set()
    for a in aliases:
        f = fold(a)
        if not f or len(a) > MAX_LEN or "\n" in a:
            errors.append(f"{a!r}: an alias is one short line, {MAX_LEN} characters at most")
        elif "[[" in a or "]]" in a:
            errors.append(f"{a!r}: aliases are plain names, never wikilinks")
        elif f in (fold(title), fold(slug.replace("-", " "))):
            errors.append(f"{a!r}: already the note's title or slug")
        elif f in seen:
            errors.append(f"{a!r}: listed twice")
        elif texts and not any(f in t for t in texts):
            errors.append(f"{a!r}: appears in none of the note's sources, so it would be an invention")
        seen.add(f)
    return path, errors


def write_aliases(path, aliases, date):
    """Replace or insert `aliases:` after `keywords:` (or the sources), bump generated.at. Returns changed."""
    text = open(path, encoding="utf-8").read()
    fm, _ = split_note(text)
    current = [str(x) for x in (fm.get("aliases") or [])] if isinstance(fm.get("aliases"), list) else []
    if current == list(aliases):
        return False
    lines = text.split("\n")
    end = next(i for i, l in enumerate(lines[1:], start=1) if l == "---")
    ai = next((i for i in range(1, end) if lines[i].startswith("aliases:")), None)
    new = ["aliases: [" + ", ".join(json.dumps(a, ensure_ascii=False) for a in aliases) + "]"] if aliases else []
    if ai is not None:
        j = ai + 1
        while j < end and lines[j].startswith("  - "):
            j += 1
        lines[ai:j] = new
    elif aliases:
        ki = next((i for i in range(1, end) if lines[i].startswith("keywords:")), None)
        if ki is not None:
            at = keywords_span(lines, ki)[1]
        else:
            at = max((i for i in range(1, end) if lines[i].startswith(("sources:", "further_sources:"))), default=end - 1) + 1
            while at < end and lines[at].startswith("  - "):
                at += 1
        lines[at:at] = new
    bump_stamp(lines, date)
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("vault")
    ap.add_argument("slug", nargs="?")
    ap.add_argument("aliases", nargs="*")
    ap.add_argument("--from-file")
    ap.add_argument("--reason")
    ap.add_argument("--run")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--date", default=None)
    a = ap.parse_args()
    root = a.vault
    if a.auto and not a.reason:
        sys.exit("error: --auto requires --reason, since an unattended write with no recorded reason cannot be audited")
    if a.from_file:
        batch = json.load(open(a.from_file, encoding="utf-8"))
    elif a.slug:
        batch = {a.slug: a.aliases}
    else:
        sys.exit("usage: apply_aliases.py <vault> <slug> alias [alias ...] | --from-file batch.json")

    checked, refused = {}, 0
    for slug, aliases in batch.items():
        aliases = [str(x).strip() for x in aliases]
        path, errors = check(root, slug, aliases)
        if errors:
            refused += 1
            for e in errors:
                print(f"REFUSED {slug}: {e}")
        else:
            checked[slug] = (path, aliases)
    if refused:
        print(f"{refused} note(s) refused; nothing written for them")
    if a.dry_run:
        for slug, (_, aliases) in checked.items():
            print(f"{slug} gets aliases: {', '.join(aliases) if aliases else '(none)'}")
        print(f"dry run: {len(checked)} note(s) pass, nothing written")
        sys.exit(1 if refused else 0)

    date = a.date or stamp()
    changed = []
    for slug, (path, aliases) in checked.items():
        if write_aliases(path, aliases, date):
            changed.append((path, aliases))
            print(f"{slug}: aliases {', '.join(aliases) if aliases else 'removed'}")
        else:
            print(f"{slug}: aliases already as given")
    if changed and a.reason:
        hist = os.path.join(root, "augment_wiki/history.jsonl")
        with open(hist, "a", encoding="utf-8") as f:
            for path, aliases in changed:
                what = f"Aliases set: {', '.join(aliases)}" if aliases else "Aliases removed"
                f.write(json.dumps(ledger_entry(root, path, f"{what}. {a.reason}", a.auto, a.run),
                                   ensure_ascii=False) + "\n")
        print(f"history: {len(changed)} entry(ies) appended{' (auto)' if a.auto else ''}{' run=' + a.run if a.run else ''}")
        subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "compact_index.py"), root],
                       check=False)
    elif changed:
        print("history: nothing appended (no --reason given); record the write yourself")
    sys.exit(1 if refused else 0)


if __name__ == "__main__":
    main()
