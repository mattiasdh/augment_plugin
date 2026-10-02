#!/usr/bin/env python3
"""The memory a session starts with (reference/memory.md).

A SessionStart hook in Code and Cowork, on startup, resume, clear and compact, so
the memory survives a compaction as well as a restart. In Chat, where no hook
runs, ACTIVATE calls it through augment-runner. Prints nothing at all outside a
vault, when memory is disabled, or when there are no active cards, so it is safe
as a global hook.

It reads the cards themselves rather than index.md, so a card written since the
last cycle is already there. Every active card is offered, in three bands: cards
scoped to the project the session is opened on, then global ones, then cards
scoped to anything else (a client, a skill, a workflow), until
`memory.inject_chars` (6000 by default) is spent; the rest are counted, and RECALL
finds them. Scope orders the list and never hides a card: a session opened on the
vault is rarely "in" the project a card names, so a filter would keep exactly the
task-specific cards out of every session.

    memory_context.py [<vault>] [--project NAME]
"""
import argparse, os

import _memory as M


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vault", nargs="?")
    ap.add_argument("--project")
    a = ap.parse_args()
    root = os.path.abspath(a.vault) if a.vault else M.resolve_vault()
    if not root or not os.path.isfile(os.path.join(root, M.MARKER)):
        return
    cfg = M.settings(root)
    if not cfg["enabled"]:
        return
    project = (a.project or os.path.basename(M.dir_setting(os.environ.get("CLAUDE_PROJECT_DIR")) or os.getcwd())).lower()
    active = [c for c in M.load_cards(root) if c[1].get("status", "active") == "active"]
    mine = [c for c in active if project in M.scopes(c[1])]
    general = [c for c in active if "global" in M.scopes(c[1]) and c not in mine]
    other = [c for c in active if c not in mine and c not in general]
    if not active:
        return
    where = "augment_memory/card/" if root == (M.dir_setting(os.environ.get("CLAUDE_PROJECT_DIR")) or os.getcwd()) \
        else os.path.join(root, "augment_memory", "card") + "/"
    head = (f"AUGMENT MEMORY: {M.n(len(active), 'card')} for this session ({len(mine)} scoped to {project}, "
            f"{len(general)} global, {len(other)} scoped elsewhere, which apply when the task matches their scope). One line each; the card at {where}<slug>.md holds the detail, and the "
            f"recall skill searches all of them. Memory says how to work, never what is true about the domain; "
            f"the remember skill records what this session learns.")
    budget, used, out, left = int(cfg["inject_chars"]), 0, [head], 0
    for slug, fm, _ in M.sort_cards(mine) + M.sort_cards(general) + M.sort_cards(other):
        line = M.index_line(slug, fm)
        if used + len(line) > budget:
            left += 1
            continue
        out.append(line)
        used += len(line) + 1
    if left:
        out.append(f"({left} more past the {budget}-character budget; recall finds them.)")
    print("\n".join(out))


if __name__ == "__main__":
    main()
