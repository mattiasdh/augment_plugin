#!/usr/bin/env python3
"""Find memory cards by what they are about (reference/memory.md). RECALL's search.

Scores each card by the query words it carries, weighted by where: title and
keywords three, summary two, body one. Active cards only unless --all, since a
superseded card answers the question the way it used to be answered. Prints one
line per hit, best first; read the card file for the rest.

    memory_search.py <vault> <query words...> [--type T] [--scope S] [--all] [--limit N]
"""
import argparse, os, sys

import _memory as M


def score(q, fm, body):
    title = M.tokens(fm.get("title", "")) | M.tokens(" ".join(M.as_list(fm.get("keywords"))))
    summary = M.tokens(fm.get("summary", ""))
    rest = M.tokens(body)
    return sum(3 * (t in title) + 2 * (t in summary) + (t in rest) for t in q)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vault")
    ap.add_argument("query", nargs="+")
    ap.add_argument("--type", choices=M.TYPES + ("skill",))
    ap.add_argument("--scope")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--limit", type=int, default=10)
    a = ap.parse_args()
    root = os.path.abspath(a.vault)
    q = M.tokens(" ".join(a.query))
    if not q:
        print("REFUSED: no searchable words in the query")
        sys.exit(1)
    hits = []
    files = M.card_files(root)
    # A skill's own MEMORY.md is searched beside the cards, typed `skill`.
    if not a.type or a.type == "skill":
        for skill, fm, body, path in M.skill_memories(root):
            first = next((l.strip() for l in body.splitlines() if l.strip()), "")
            pseudo = {"type": "skill", "title": skill, "summary": first[:160], "keywords": [skill], "scope": ["global"],
                      "seen": fm.get("seen", 1), "status": "active"}
            s = score(q, pseudo, body)
            if s:
                hits.append((s, M.seen_of(pseudo), skill, dict(pseudo, _path=M.card_rel(path, root))))
    for slug, fm, body in M.load_cards(root):
        if a.type == "skill":
            break
        status = fm.get("status", "active")
        if not a.all and status != "active":
            continue
        if a.type and fm.get("type") != a.type:
            continue
        if a.scope and a.scope.lower() not in M.scopes(fm) and "global" not in M.scopes(fm):
            continue
        s = score(q, fm, body)
        if s:
            hits.append((s, M.seen_of(fm), slug, fm))
    hits.sort(key=lambda h: (-h[0], -h[1], h[2]))
    if not hits:
        print(f"no card matches: {' '.join(sorted(q))}")
        return
    for s, _, slug, fm in hits[:a.limit]:
        flag = "" if fm.get("status", "active") == "active" else f" {fm.get('status').upper()}"
        if fm.get("superseded_by"):
            flag += f" -> {fm['superseded_by']}"
        where = fm.get("_path") or M.card_rel(files.get(slug, os.path.join(root, M.CARD_DIR, slug + ".md")), root)
        print(f"{s:>3}  {where}  [{fm.get('type')}, {', '.join(M.scopes(fm))}]{flag}  "
              f"{fm.get('summary', '')}")
    if len(hits) > a.limit:
        print(f"... {len(hits) - a.limit} more; narrow the query or raise --limit")


if __name__ == "__main__":
    main()
