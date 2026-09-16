#!/usr/bin/env python3
"""Apply, or remove, confirmed convergence pairs as `Keywords` tags (VERIFY step 5, CONTRACT §7).

Given one or more `slugA::slugB` pairs the person has confirmed, writes `[[slugB]]`
into slugA's frontmatter `keywords:` list. **The tag is directional and one-way by
default**: the path back is Obsidian's own backlink from slugB, so writing the
reverse tag as well duplicates in frontmatter what the graph already carries, and
most confirmed adjacencies are genuinely asymmetric (a project is worth tagging with
the method it applies; the method is not worth tagging with every project that ever
applied it). `--both` writes the reverse tag too, for the case where each note
genuinely earns the other in its own right. If a note has no `keywords:` key yet, one
is inserted after its `kind:` (or `type:`) key, the canonical position (CONTRACT §4). Each edited note's `updated:`
is bumped to the current local timestamp in `generated.at`, `YYYY-MM-DD HH:MM`
(CONTRACT §4). Idempotent:
a tag already present is left alone.

`--remove` reverses the operation for a pair whose edge no longer holds, the decay lane's
proposal (CONTRACT §12). It drops the tag in the same direction it would write it, empties a `keywords:` key rather
than leaving `[]` behind, and bumps `updated:`. Removal is a person's decision at VERIFY,
never a cycle's, and it is the one place this system takes something away rather than
superseding it: an unsourced tag carries no statement, so there is nothing to supersede,
and the removal is recoverable from git and from the note's history entry.

Pinned so the recurring VERIFY step is not a hand-edit across twenty files, which
is where a bidirectional tagging goes wrong (a tag added on one side only, a
a missing `keywords:` key, a forgotten stamp). It writes `Keywords` tags only, the
unsourced Tier-2 layer; it never writes a sourced `## Links` relationship, which
carries a `Source:` and stays a considered edit. Refuses (exit 1) any slug that
does not resolve to exactly one wiki note under `augment_wiki/`, so a typo fails loud
rather than tagging the wrong note.

A run that actually changes a tag then regenerates `relations.md`, the theme
bodies and the hubs (DREAM phase 7's matched cascade), the same three a keyword
edit can invalidate: candidate scores in `relations.md` are computed against
current membership, and a theme's body is built directly from the `Keywords`
back-references it just gained or lost. Without this the view a person reads
right after approving a batch is still the one from before it, until the next
DREAM run catches up (a real gap: VERIFY's own 2026-08-16 membership batch left
`relations.md` stale for four hours, and the held items it queued cited scores
that had already moved). A run where every pair was already applied, or every
`--remove` already absent, changes nothing and skips the regeneration.

Usage:
    python3 apply_keywords.py . a-note::another-note   # a-note gets Keyword: another-note
    python3 apply_keywords.py . --both a::b            # each gets the other
    python3 apply_keywords.py . --date '2026-08-09 14:20' a::b c::d
    python3 apply_keywords.py . --remove a-note::another-note
    python3 apply_keywords.py . --dry-run a::b         # state the writes, change nothing
"""
import glob, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gen_util import split_note, links_in, stamp

WIKILINK = re.compile(r"\[\[([^\]|]+)")


def ledger_entry(root, path, reason, auto, run):
    """A history line for a note this run changed, built from its current index entry.

    The ledger is what makes an autonomous write auditable and revertible, so the
    script that makes the write is the thing that records it: a cycle that applies
    twenty tags and hand-writes twenty JSON lines afterwards will eventually write
    nineteen (CONTRACT §9, the same argument that pinned the hasher and the
    compaction). `auto` separates a write the cycle made on its own judgement from
    one a person confirmed, and `run` groups a night's writes so `undo_run.py` can
    lift exactly that batch back out.
    """
    rel = os.path.relpath(path, root).replace(os.sep, "/")
    base = {}
    idx = os.path.join(root, "augment_wiki/index.jsonl")
    if os.path.exists(idx):
        with open(idx, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                if d.get("id") == rel:
                    base = d
    if not base:                                   # a note minted this cycle, not yet compacted
        fm, _ = split_note(open(path, encoding="utf-8").read())
        strip = lambda v: re.sub(r'[\[\]"]', "", str(v or "")).strip()
        base = {"id": rel, "type": strip(fm.get("type")), "kind": strip(fm.get("kind")),
                "title": "", "status": "#current", "compiled_from": [], "flags": 0}
    entry = {k: base.get(k) for k in
             ("id", "type", "kind", "title", "status", "compiled", "compiled_from", "flags")
             if base.get(k) is not None}
    entry["note"] = reason
    if auto:
        entry["auto"] = True
    if run:
        entry["run"] = run
    return entry


def locate(root, slug):
    hits = [p for p in glob.glob(os.path.join(root, "augment_wiki/**", slug + ".md"), recursive=True)
            if "/_system/" not in p]
    if len(hits) != 1:
        sys.exit(f"error: {slug!r} resolves to {len(hits)} notes, expected 1: {hits}")
    return hits[0]


def is_theme(path):
    """True for a theme note, whose body is generated and which is never back-tagged."""
    return os.sep + "theme" + os.sep in path or "/theme/" in path


def bump_stamp(lines, date):
    """Rewrite the `at:` line inside the frontmatter's `generated` block (CONTRACT §4).

    Scoped to the lines under `generated:` so a body line reading `at:` cannot be hit,
    and bounded to the frontmatter, which ends at the closing fence.
    """
    inblock = False
    for i, l in enumerate(lines[1:12], start=1):
        if l == "---":
            break
        if l.startswith("generated:"):
            inblock = True
            continue
        if inblock and l.startswith("  at:"):
            lines[i] = f"  at: {date}"
            return
        if inblock and not l.startswith("  "):
            inblock = False
    sys.exit("error: no generated.at line to bump; note is not on the current schema")


def keywords_span(lines, ki):
    """The line range a `keywords:` value occupies, starting at `ki`.

    Almost every note in this vault writes `keywords:` as a single flow-style
    line (CONTRACT §4's own documented shape), which is all the line-based
    rewrite below ever assumed. One note had it in YAML block-list style
    instead, `keywords:` alone followed by `  - "[[x]]"` lines, which parses
    identically through `split_note` (a real reader, `yaml.safe_load`) but
    doesn't end in `]`, so the old code's `.rstrip("]")` on a bare `keywords:`
    line found nothing to strip and appended a fragment onto it, corrupting
    the file and stranding the block lines below as orphaned YAML (INCIDENTS,
    2026-09-10). This walks past any such block lines so both callers below
    replace the whole span, never a partial line.
    """
    j = ki + 1
    while j < len(lines) and lines[j].startswith("  - "):
        j += 1
    return ki, j                                            # [ki, j) is the span


def drop_tag(path, tag, date):
    """Remove [[tag]] from path's Keywords value (drop the key if it empties); bump updated:. Idempotent."""
    text = open(path, encoding="utf-8").read()
    fm, _ = split_note(text)
    remaining = [k for k in links_in(fm.get("keywords")) if k != tag]
    if len(remaining) == len(links_in(fm.get("keywords"))):
        return False                                       # not tagged, no-op
    lines = text.split("\n")
    ki = next((i for i, l in enumerate(lines) if l.startswith("keywords:")), None)
    if ki is None:
        return False
    start, end = keywords_span(lines, ki)
    if remaining:
        lines[start:end] = ["keywords: [" + ", ".join(f'"[[{k}]]"' for k in remaining) + "]"]
    else:
        del lines[start:end]                                # an empty list is not a value (CONTRACT §4)
    bump_stamp(lines, date)
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return True


def add_tag(path, tag, date):
    """Add [[tag]] to path's Keywords value (insert the key if absent); bump updated:. Idempotent."""
    text = open(path, encoding="utf-8").read()
    fm, _ = split_note(text)
    existing = links_in(fm.get("keywords"))
    if tag in existing:
        return False                                       # already tagged, no-op
    lines = text.split("\n")
    ki = next((i for i, l in enumerate(lines) if l.startswith("keywords:")), None)
    if ki is not None:
        start, end = keywords_span(lines, ki)
        merged = existing + [tag]
        lines[start:end] = ["keywords: [" + ", ".join(f'"[[{k}]]"' for k in merged) + "]"]
    else:
        anchor = next((i for i, l in enumerate(lines)
                       if l.startswith(("kind:", "type:"))), None)
        if anchor is None:
            sys.exit(f"error: {path} has no type:/kind: line to place keywords after")
        lines.insert(anchor + 1, f'keywords: ["[[{tag}]]"]')
    bump_stamp(lines, date)
    open(path, "w", encoding="utf-8").write("\n".join(lines))
    return True


def regenerate_views(root):
    """Re-run the cascade a keyword edit can invalidate: relations.md, the theme
    bodies, then the hubs, DREAM phase 7's own order. Each generator is
    idempotent (`write_if_changed`), so running one with nothing to say is a
    no-op, not a spurious rewrite.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    for script in ("gen_relations.py", "gen_themes.py", "gen_hubs.py"):
        r = subprocess.run([sys.executable, os.path.join(here, script), root],
                            capture_output=True, text=True)
        if r.returncode != 0:
            print(f"warning: {script} failed to regenerate:\n{r.stderr}", file=sys.stderr)
        elif r.stdout.strip():
            print(r.stdout.strip())


def main():
    rest = sys.argv[1:]
    root = "."
    if rest and not rest[0].startswith("--") and "::" not in rest[0]:
        root, rest = rest[0], rest[1:]        # first positional is the vault root
    date = stamp()
    remove = False
    dry = False
    both = False
    reason = None
    run = None
    auto = False
    out = []
    while rest:
        a = rest.pop(0)
        if a == "--date":
            date = rest.pop(0)
        elif a == "--reason":
            reason = rest.pop(0)
        elif a == "--run":
            run = rest.pop(0)
        elif a == "--auto":
            auto = True
        elif a == "--remove":
            remove = True
        elif a == "--dry-run":
            dry = True
        elif a == "--both":
            both = True
        elif "::" in a:
            out.append(tuple(a.split("::", 1)))
        else:
            sys.exit(f"error: expected slugA::slugB, got {a!r}")
    if not out:
        sys.exit("usage: apply_keywords.py . [--remove] [--dry-run] [--both] "
                 "[--reason '...'] [--run <id>] [--auto] "
                 "slugA::slugB [slugC::slugD ...] [--date 'YYYY-MM-DD HH:MM']\n"
                 "  slugA::slugB writes [[slugB]] onto slugA only; --both also writes the reverse\n"
                 "  --reason writes each changed note's history entry; --auto marks it a cycle write")
    if auto and not reason:
        sys.exit("error: --auto requires --reason, since an unattended write with no "
                 "recorded reason cannot be audited at VERIFY")

    # resolve all slugs first, so a typo fails before any write
    paths = {}
    for a, b in out:
        for s in (a, b):
            if s not in paths:
                paths[s] = locate(root, s)

    # `--dry-run` states the writes without making them, so VERIFY step 5 can put the
    # actual edit to the person instead of describing the convention in prose. The
    # shape is one line per candidate, opening with the note being changed and saying
    # the change in words; four rewrites stand behind it (INCIDENTS, 2026-08-30 and
    # 2026-09-01). Slugs print bare rather than as [[wikilinks]], since the line is
    # prose for a person to read, not a link to resolve. Reads the same `is_theme` and
    # direction branches the real run takes, so what it prints is what the run does.
    if dry:
        for a, b in out:
            theme = is_theme(paths[b])
            verb = "loses" if remove else "gets"
            if theme:
                print(f"{a} {verb} Theme membership: {b}.")
            elif both:
                print(f"Both {a} and {b} {'lose' if remove else 'get'} each other as Keyword.")
            else:
                print(f"{a} {verb} Keyword: {b}.")
        print(f"dry run: {len(out)} tag(s), nothing written")
        return

    any_write = False
    changed = []
    for a, b in out:
        # Membership is one-directional: a member points at its theme, never the
        # reverse. A theme's body is generated from those back-references, so a
        # keyword written onto the theme is both wrong in direction and erased by
        # the next `gen_themes` run, which makes it a silent no-op rather than a
        # visible error.
        theme = is_theme(paths[b])
        act = drop_tag if remove else add_tag
        wa = act(paths[a], b, date)
        wb = act(paths[b], a, date) if (both and not theme) else None
        if wa or wb:
            any_write = True
        verbed = "removed" if remove else "gained"
        if wa:
            changed.append((paths[a], f"Keyword [[{b}]] {verbed}"))
        if wb:
            changed.append((paths[b], f"Keyword [[{a}]] {verbed}"))
        verb, already = ("removed", "already absent") if remove else ("applied", "already present")
        if theme:
            state = f"membership {verb} (one way, theme)" if wa else f"membership {already}"
            print(f"{a} -> {b}: {state}")
        elif both:
            if wa and wb:
                state = f"{verb} both ways"
            elif not (wa or wb):
                state = already
            else:
                state = f"half {already}"
            print(f"{a} <-> {b}: {state}")
        else:
            print(f"{a} -> {b}: {verb if wa else already} (one way)")
    if remove:
        print("record each declined removal in augment_wiki/relations_dismissed.jsonl as "
              '{"pair": [a, b], "ruled": "<date>", "ruling": "keep"} so it is not re-proposed')
    print(f"done: {len(out)} pair(s), stamped {date}")
    if changed and reason:
        # One line per note actually changed, grouped so a note that gained two tags
        # in one call carries one entry naming both, which is what a person reading
        # the ledger wants and what `undo_run.py` reads back.
        per_note = {}
        for path, what in changed:
            per_note.setdefault(path, []).append(what)
        hist = os.path.join(root, "augment_wiki/history.jsonl")
        with open(hist, "a", encoding="utf-8") as f:
            for path, whats in per_note.items():
                note = f"{'; '.join(whats)}. {reason}"
                f.write(json.dumps(ledger_entry(root, path, note, auto, run),
                                   ensure_ascii=False) + "\n")
        print(f"history: {len(per_note)} entry(ies) appended"
              f"{' (auto)' if auto else ''}{' run=' + run if run else ''}")
        subprocess.run([sys.executable,
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), "compact_index.py"),
                        root], check=False)
    elif changed:
        print("history: nothing appended (no --reason given); record the write yourself")
    if any_write:
        regenerate_views(root)


if __name__ == "__main__":
    main()
