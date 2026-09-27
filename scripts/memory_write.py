#!/usr/bin/env python3
"""The one writer of the memory layer (reference/memory.md). Both tiers use it.

  add        a new card; refused when an active card is already about the same
             thing (score >= 0.5), which is then named so the caller confirms it
             with `seen` or amends it with `update` instead of writing a second one
  seen       the memory was confirmed or relearned: seen + 1, updated now
  update     replace fields of a card; the body only when one is given
  supersede  the old card points at the one replacing it and stops being active
  archive    no longer loaded or listed; the person's call, taken at the sweep
  offer      content found while working, parked for the source layer, where the
             sweep moves it through write capture; never a card

Every write refuses the common secret shapes, and a card with no `--by` is refused,
because the producer is read from the runtime and never defaulted.

    memory_write.py <vault> add --type tool --title "..." --summary "..." --by augment/<runtime>
                    [--scope global|<project>[,<project>]] [--keywords a,b] [--body TEXT | --body-file F] [--distinct]
    memory_write.py <vault> seen <slug>
    memory_write.py <vault> update <slug> [--title|--summary|--type|--scope|--keywords|--body|--body-file] [--by]
    memory_write.py <vault> supersede <old-slug> <new-slug>
    memory_write.py <vault> archive <slug>
    memory_write.py <vault> offer --title "..." --by augment/<runtime> (--body TEXT | --body-file F)
"""
import argparse, os, sys

import _memory as M


def fail(msg):
    print(f"REFUSED: {msg}")
    sys.exit(1)


def body_of(a):
    if getattr(a, "body_file", None):
        p = a.body_file
        if p.startswith("scratch/"):
            import tempfile
            p = os.path.join(tempfile.gettempdir(), "augment-scratch", os.path.basename(p[8:]))
        return open(p, encoding="utf-8").read()
    return getattr(a, "body", None)


def check_fields(title=None, summary=None, typ=None):
    if title is not None:
        if not title.strip():
            fail("empty title")
        if len(title.split()) > M.TITLE_WORDS:
            fail(f"title has {len(title.split())} words; ten at most")
    if summary is not None:
        if not summary.strip() or "\n" in summary:
            fail("the summary is one non-empty line")
        if len(summary) > M.SUMMARY_MAX:
            fail(f"summary is {len(summary)} characters; {M.SUMMARY_MAX} at most")
    if typ is not None and typ not in M.TYPES:
        fail(f"type must be one of {', '.join(M.TYPES)}")


def check_secret(*texts):
    for t in texts:
        hit = M.secret_in(t or "")
        if hit:
            fail(f"this looks like a secret ({hit}). Memory never holds credentials; describe where "
                 "the secret lives instead, and do not reformat it to get past this check.")


def card_path(root, slug):
    return os.path.join(root, M.CARD_DIR, slug + ".md")


def read(root, slug):
    p = card_path(root, slug)
    if not os.path.isfile(p):
        fail(f"no card {slug} (augment_memory/card/{slug}.md)")
    fm, body = M.split_note(open(p, encoding="utf-8").read())
    return p, fm, body


def write(p, fm, body):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(M.render(fm, body))


def split_list(v):
    return [x.strip() for x in (v or "").split(",") if x.strip()]


def cmd_add(root, a):
    body = body_of(a) or ""
    check_fields(a.title, a.summary, a.type)
    check_secret(a.title, a.summary, a.keywords, body)
    fm = {"type": a.type, "title": a.title.strip(), "summary": a.summary.strip(), "status": "active",
          "scope": split_list(a.scope) or ["global"], "keywords": split_list(a.keywords),
          "seen": 1, "created": M.stamp(), "updated": M.stamp(), "by": a.by}
    if not a.distinct:
        mine = M.card_tokens(fm)
        best = max(((M.jaccard(mine, M.card_tokens(f)), s) for s, f, _ in M.load_cards(root)
                    if f.get("status", "active") == "active"), default=(0.0, ""))
        if best[0] >= M.SAME:
            fail(f"LIKELY SAME as active card {best[1]} ({best[0]:.2f}). Confirm it with `seen {best[1]}`, "
                 f"amend it with `update {best[1]}`, or pass --distinct if the two really differ.")
    slug = M.slugify(a.title)
    if os.path.exists(card_path(root, slug)):
        fail(f"a card named {slug} exists already; update it, or choose a title that says what differs")
    write(card_path(root, slug), fm, body)
    print(f"added augment_memory/card/{slug}.md ({a.type}, {', '.join(fm['scope'])})")


def cmd_seen(root, a):
    p, fm, body = read(root, a.slug)
    fm["seen"] = M.seen_of(fm) + 1
    fm["updated"] = M.stamp()
    write(p, fm, body)
    print(f"{a.slug}: seen {fm['seen']}")


def cmd_update(root, a):
    p, fm, body = read(root, a.slug)
    new_body = body_of(a)
    check_fields(a.title, a.summary, a.type)
    check_secret(a.title, a.summary, a.keywords, new_body)
    for k in ("title", "summary", "type", "by"):
        v = getattr(a, k)
        if v is not None:
            fm[k] = v.strip()
    if a.scope is not None:
        fm["scope"] = split_list(a.scope) or ["global"]
    if a.keywords is not None:
        fm["keywords"] = split_list(a.keywords)
    fm["updated"] = M.stamp()
    write(p, fm, body if new_body is None else new_body)
    print(f"updated augment_memory/card/{a.slug}.md")


def cmd_supersede(root, a):
    if a.old == a.new:
        fail("a card cannot supersede itself")
    read(root, a.new)
    p, fm, body = read(root, a.old)
    fm["status"], fm["superseded_by"], fm["updated"] = "superseded", a.new, M.stamp()
    write(p, fm, body)
    print(f"{a.old} superseded by {a.new}")


def cmd_archive(root, a):
    p, fm, body = read(root, a.slug)
    fm["status"], fm["updated"] = "archived", M.stamp()
    write(p, fm, body)
    print(f"{a.slug} archived")


def cmd_offer(root, a):
    body = body_of(a)
    if not body or not body.strip():
        fail("an offer needs the drafted content as its body")
    check_fields(title=a.title)
    check_secret(a.title, body)
    now = M.stamp()
    slug = now[:10] + "-" + M.slugify(a.title)
    p = os.path.join(root, M.OFFER_DIR, slug + ".md")
    if os.path.exists(p):
        fail(f"an offer {slug} exists already")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    text = (f"---\ntitle: {M.q(a.title.strip())}\noffered: {now}\nassisted_by: {a.by}\n---\n"
            f"{body.strip()}\n")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"offered augment_memory/offers/{slug}.md; the sweep moves it into the source layer through write capture")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("vault")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def body_args(p):
        g = p.add_mutually_exclusive_group()
        g.add_argument("--body")
        g.add_argument("--body-file")

    p = sub.add_parser("add")
    p.add_argument("--type", required=True, choices=M.TYPES)
    p.add_argument("--title", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--by", required=True)
    p.add_argument("--scope")
    p.add_argument("--keywords")
    p.add_argument("--distinct", action="store_true")
    body_args(p)

    p = sub.add_parser("seen")
    p.add_argument("slug")

    p = sub.add_parser("update")
    p.add_argument("slug")
    for k in ("--title", "--summary", "--scope", "--keywords", "--by"):
        p.add_argument(k)
    p.add_argument("--type", choices=M.TYPES)
    body_args(p)

    p = sub.add_parser("supersede")
    p.add_argument("old")
    p.add_argument("new")

    p = sub.add_parser("archive")
    p.add_argument("slug")

    p = sub.add_parser("offer")
    p.add_argument("--title", required=True)
    p.add_argument("--by", required=True)
    body_args(p)

    a = ap.parse_args()
    root = os.path.abspath(a.vault)
    if not os.path.isfile(os.path.join(root, M.MARKER)):
        fail(f"{root} is not a vault (no augment_wiki/config.yaml)")
    if not M.settings(root)["enabled"]:
        fail("memory is disabled in this vault's config.yaml (memory.enabled: false)")
    {"add": cmd_add, "seen": cmd_seen, "update": cmd_update, "supersede": cmd_supersede,
     "archive": cmd_archive, "offer": cmd_offer}[a.cmd](root, a)


if __name__ == "__main__":
    main()
