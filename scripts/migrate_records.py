#!/usr/bin/env python3
"""One-time rename of session records to `<id> <slug>.md` (reference/sessions.md).

Before 2026-11-02 a record was `augment_sessions/<id>.md`, which says nothing to a
person browsing the folder. It is now `<id> <slug>.md`, the slug taken from the title.
This moves each bare-id record with `git mv`, so its history follows, rewrites the
links to it in the briefings (`augment_wiki/view/`), and writes the index. A link
found under `notes/` is the person's text: it is reported, never rewritten.

    migrate_records.py <vault>            report what would move
    migrate_records.py <vault> --apply    move, rewrite links, write augment_sessions/index.md
"""
import _cli
import glob, os, re, subprocess, sys
_cli.help_guard()

import _memory as M
import record_write as R


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = os.path.abspath(args[0] if args else ".")
    apply = "--apply" in sys.argv
    d = os.path.join(root, R.DIR)
    if not os.path.isdir(d):
        sys.exit(f"no {R.DIR}/ here")
    moves = {}
    for f in sorted(os.listdir(d)):
        if f.endswith(".md") and R.ID_RE.match(f[:-3]):
            fm, _ = M.split_note(open(os.path.join(d, f), encoding="utf-8").read())
            new = R.file_of(f[:-3], fm.get("title"))
            if new != f:
                moves[f[:-3]] = new[:-3]
    views = glob.glob(os.path.join(root, "augment_wiki", "view", "**", "*.md"), recursive=True)
    rx = re.compile(r"(augment_sessions/)(R-\d{6}-[a-z2-7]{4})(?=[|\]#]|\.md)")
    for old, new in moves.items():
        print(f"{'moving' if apply else 'would move'} {R.DIR}/{old}.md -> {R.DIR}/{new}.md")
        if apply:
            r = subprocess.run(["git", "mv", f"{R.DIR}/{old}.md", f"{R.DIR}/{new}.md"], cwd=root, capture_output=True, text=True)
            if r.returncode:
                os.rename(os.path.join(d, old + ".md"), os.path.join(d, new + ".md"))
    changed = 0
    for p in views:
        t = open(p, encoding="utf-8").read()
        n = rx.sub(lambda m: m.group(1) + moves.get(m.group(2), m.group(2)), t)
        if n != t:
            changed += 1
            print(f"{'rewrote' if apply else 'would rewrite'} links in {os.path.relpath(p, root)}")
            if apply:
                open(p, "w", encoding="utf-8", newline="").write(n)
    for p in glob.glob(os.path.join(root, "notes", "**", "*.md"), recursive=True):
        for m in rx.finditer(open(p, encoding="utf-8", errors="replace").read()):
            if m.group(2) in moves:
                print(f"NOT TOUCHED (your note): {os.path.relpath(p, root)} links {m.group(2)}")
    if apply:
        print(f"moved {len(moves)} record(s), rewrote {changed} view(s); wrote {R.write_index(root)}")
    else:
        print(f"{len(moves)} record(s) to move, {changed} view(s) to rewrite; run with --apply")


if __name__ == "__main__":
    main()
