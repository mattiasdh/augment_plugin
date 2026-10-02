#!/usr/bin/env python3
"""Recall without being asked: the memory cards a prompt is about (reference/memory.md).

A UserPromptSubmit hook in Code and Cowork. Session start already lists every
active card in one line; this names the few the prompt at hand is actually about,
so the model opens those cards before it starts, instead of relearning what an
earlier session wrote down. In Chat no hook runs, and the connector's `activate`
text asks for the same search instead.

Scoring rewards distinctive words: a prompt word scores by where the card carries
it (title or keywords three, summary two) times how rare it is across the cards,
so "Coda" or "Affinity" counts and "file" or "post" barely does. The body is not
scored: it is long, and long text matches everything a little. Cards over the
threshold, and within 40 % of the best, are named, three at most. Silent outside
a vault, when memory is off, for prompts of fewer than three words, and when
nothing clears the bar.

    memory_recall.py --hook                 reads {"prompt": ...} on stdin
    memory_recall.py <vault> <prompt words...>   prints the scores, for tuning
"""
import json, math, os, sys

import _memory as M

# Words every vault and tool conversation uses. They still count, at a third, so a
# card can be confirmed by them, but they cannot carry it alone: "can the connector
# write files" is about the connector, not about the Coda card's "connector ... write".
GENERIC = {"connector", "write", "read", "file", "folder", "note", "vault", "memory", "skill",
           "tool", "script", "plugin", "project", "session", "card", "access", "local", "update",
           "add", "make", "new", "chat", "code", "claude", "data", "work", "doc", "mcp"}

THRESHOLD = 10.0  # more than one rare word in a title: a single hit, however rare, stays silent
RELATIVE = 0.4    # and within reach of the best hit, so one strong card does not drag in weak ones
MOST = 3


def rank(root, text):
    q = M.tokens(text)
    if len(q) < 3:
        return []
    cards = [c for c in M.load_cards(root) if c[1].get("status", "active") == "active"]
    if not cards:
        return []
    fields = []
    df = {}
    for slug, fm, _ in cards:
        title = M.tokens(fm.get("title", "")) | M.tokens(" ".join(M.as_list(fm.get("keywords"))))
        summary = M.tokens(fm.get("summary", ""))
        fields.append((slug, fm, title, summary))
        for t in title | summary:
            df[t] = df.get(t, 0) + 1
    n = len(cards)
    out = []
    for slug, fm, title, summary in fields:
        s = sum((3 if t in title else 2 if t in summary else 0) * math.log(1 + n / df[t])
                * (1 / 3 if t in GENERIC else 1) for t in q if t in df)
        if s:
            out.append((round(s, 2), slug, fm))
    out.sort(key=lambda h: (-h[0], h[1]))
    return out


def select(ranked):
    if not ranked or ranked[0][0] < THRESHOLD:
        return []
    return [h for h in ranked if h[0] >= max(THRESHOLD, RELATIVE * ranked[0][0])][:MOST]


def main():
    if sys.argv[1:2] == ["--hook"]:
        try:
            prompt = str(json.load(sys.stdin).get("prompt", ""))
        except (json.JSONDecodeError, AttributeError, ValueError):
            return
        root = M.resolve_vault()
        if not root or not M.settings(root)["enabled"]:
            return
        hits = select(rank(root, prompt))
        if not hits:
            return
        lines = ["AUGMENT RECALL: this prompt matches what earlier sessions recorded. Open these cards "
                 "before working, follow them unless the person says otherwise, and name the card when it "
                 "changes what you do:"]
        here = M.dir_setting(os.environ.get("CLAUDE_PROJECT_DIR")) or os.getcwd()
        where = "augment_memory/card/" if root == here else os.path.join(root, M.CARD_DIR) + "/"
        lines += [f"- {where}{slug}.md: {fm.get('summary', '')}" for _, slug, fm in hits]
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                                 "additionalContext": "\n".join(lines)}}))
        return
    if len(sys.argv) < 3:
        sys.exit(__doc__.strip().splitlines()[-1])
    ranked = rank(os.path.abspath(sys.argv[1]), " ".join(sys.argv[2:]))
    chosen = {h[1] for h in select(ranked)}
    for s, slug, _ in ranked[:6]:
        print(f"{s:>6}  {'*' if slug in chosen else ' '} {slug}")


if __name__ == "__main__":
    main()
