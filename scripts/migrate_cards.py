#!/usr/bin/env python3
"""One-time move of flat memory cards into their type folders (reference/memory.md).

Before 2026-10-28 every card sat directly in `augment_memory/card/`. A card now
lives in `augment_memory/card/<type>/<slug>.md`, so the folder reads as an
overview in Obsidian's file list. The readers accept both layouts, so this can
run whenever the deployed connector has been updated; it moves each flat card
with `git mv`, so a card's history follows it, and regenerates the index. Wiki
links `[[slug]]` keep resolving, since Obsidian links by file name.

    migrate_cards.py <vault>            report what would move
    migrate_cards.py <vault> --apply    move, then regenerate augment_memory/index.md
"""
import _cli
import os, subprocess, sys
_cli.help_guard()

import _memory as M


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = os.path.abspath(args[0] if args else ".")
    apply = "--apply" in sys.argv
    d = os.path.join(root, M.CARD_DIR)
    if not os.path.isdir(d):
        sys.exit("no augment_memory/card/ here")
    moves, bad = [], []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        fm, _ = M.split_note(open(os.path.join(d, f), encoding="utf-8").read())
        t = fm.get("type")
        if t not in M.TYPES:
            bad.append(f"{f}: type {t!r}")
            continue
        moves.append((os.path.join(d, f), os.path.join(d, t, f)))
    for src, dst in moves:
        rel = lambda p: os.path.relpath(p, root)
        if not apply:
            print(f"would move {rel(src)} -> {rel(dst)}")
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst):
            bad.append(f"{rel(dst)} exists already; {rel(src)} left in place")
            continue
        r = subprocess.run(["git", "mv", rel(src), rel(dst)], cwd=root, capture_output=True, text=True)
        if r.returncode:
            os.rename(src, dst)        # outside git, a plain move
    for b in bad:
        print(f"SKIPPED {b}")
    if apply:
        M.write_index(root)
        print(f"moved {len(moves) - len([b for b in bad if 'exists already' in b])} card(s) into type folders; index regenerated")
    else:
        print(f"{len(moves)} card(s) to move; run with --apply")


if __name__ == "__main__":
    main()
