#!/usr/bin/env python3
"""Regenerate augment_memory/index.md and check the memory layer (reference/memory.md).

The index is one line per active card, grouped by type, most reinforced first,
capped at `memory.index_cap` lines (150 by default), with a closing count of what
the cap left out, which RECALL still finds. It is overwritten wholesale; a hand
edit does not survive.

The same pass reports for DREAM's queue, one line each:

  DEFECT         a card the writer would have refused: missing or invalid field,
                 over-long summary or title, a supersession pointing nowhere, a
                 secret. Exit 1 when any is found.
  LIKELY SAME    two active cards scoring >= 0.4 on title, summary and keywords:
                 merge candidates. The merge is a supersession, cheap to undo.
  UNSTABLE       an active card edited more than three times in the last seven
                 days (git history): a memory that keeps moving is usually content
                 or a skill's rules growing inside a card, for the sweep to rehome.
  DECAY          an active card seen once and untouched for `memory.decay_days`:
                 an archive proposal for the sweep, never archived here.
  OFFER          content waiting in augment_memory/offers/ for the sweep to move
                 into the source layer.

    gen_memory_index.py <vault> [--check]     --check reports without writing
"""
import argparse, collections, datetime, os, subprocess, sys

import _memory as M


def defects(slug, fm, body, slugs):
    out = []
    if fm.get("type") not in M.TYPES:
        out.append(f"type {fm.get('type')!r} is not one of {', '.join(M.TYPES)}")
    if fm.get("status", "active") not in M.STATUSES:
        out.append(f"status {fm.get('status')!r} is not one of {', '.join(M.STATUSES)}")
    for k in ("title", "summary", "created", "updated", "by"):
        if not fm.get(k):
            out.append(f"no {k}")
    if len(str(fm.get("summary", ""))) > M.SUMMARY_MAX:
        out.append(f"summary over {M.SUMMARY_MAX} characters")
    if len(body.strip()) > M.BODY_MAX:
        out.append(f"body over {M.BODY_MAX} characters: a skill reference or a note, not a card")
    if len(str(fm.get("title", "")).split()) > M.TITLE_WORDS:
        out.append(f"title over {M.TITLE_WORDS} words")
    if fm.get("status") == "superseded" and fm.get("superseded_by") not in slugs:
        out.append(f"superseded_by {fm.get('superseded_by')!r} names no card")
    hit = M.secret_in(" ".join([str(fm.get("title", "")), str(fm.get("summary", "")), body]))
    if hit:
        out.append(f"looks like a secret ({hit})")
    return out


def recent_edits(root):
    """Commits touching each card within the churn window, from git; empty outside a repository."""
    try:
        out = subprocess.run(["git", "-C", root, "log", "--no-merges", f"--since={M.CHURN_DAYS}.days",
                              "--format=", "--name-only", "--", M.CARD_DIR],
                             capture_output=True, text=True, timeout=20).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    return collections.Counter(os.path.basename(l)[:-3] for l in out.splitlines() if l.endswith(".md"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vault")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.vault)
    cfg = M.settings(root)
    cards = M.load_cards(root)
    slugs = {s for s, _, _ in cards}
    report, bad = [], 0

    for slug, fm, body in cards:
        for d in defects(slug, fm, body, slugs):
            report.append(f"DEFECT       {slug}: {d}")
            bad += 1

    active = [c for c in cards if c[1].get("status", "active") == "active"]
    toks = {s: M.card_tokens(fm) for s, fm, _ in active}
    names = sorted(toks)
    for i, x in enumerate(names):
        for y in names[i + 1:]:
            j = M.jaccard(toks[x], toks[y])
            if j >= M.CANDIDATE:
                report.append(f"LIKELY SAME  {x} :: {y} ({j:.2f})")

    horizon = (datetime.date.today() - datetime.timedelta(days=int(cfg["decay_days"]))).isoformat()
    for slug, fm, _ in active:
        if M.seen_of(fm) <= 1 and str(fm.get("updated", ""))[:10] < horizon:
            report.append(f"DECAY        {slug}: seen once, untouched since {str(fm.get('updated'))[:10]}")

    edits = recent_edits(root)
    for slug, fm, _ in active:
        if edits.get(slug, 0) > M.CHURN_EDITS:
            report.append(f"UNSTABLE     {slug}: {edits[slug]} edits in {M.CHURN_DAYS} days; rehome what keeps "
                          "changing (a skill's references, or the notes) and keep the card to routing")

    od = os.path.join(root, M.OFFER_DIR)
    for f in sorted(os.listdir(od)) if os.path.isdir(od) else []:
        if f.endswith(".md"):
            report.append(f"OFFER        augment_memory/offers/{f}")

    text, indexed = M.render_index(cards, int(cfg["index_cap"]))

    p = os.path.join(root, M.INDEX)
    changed = not os.path.isfile(p) or open(p, encoding="utf-8").read() != text
    if not a.check and cards and changed:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    verb = "would change" if a.check and changed else "written" if changed and cards else "unchanged"
    print(f"memory: {M.n(len(cards), 'card')}, {len(active)} active, {indexed} indexed; index {verb}")
    for r in report:
        print(r)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
