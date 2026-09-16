#!/usr/bin/env python3
"""Regenerate the body of each theme note from Keywords back-references (CONTRACT §3, §11).

A theme note (`augment_wiki/theme/<slug>.md`) is a curated anchor: it is *minted* by
hand at VERIFY (deciding the topic earns an anchor and adding the index entry),
but its BODY is generated, like a hub. The body is the list of content notes
whose `keywords:` list points at the theme. This script fills that list; it never
creates, renames or deletes a theme note, because minting and retiring are
curation decisions, not mechanical ones. It preserves each theme's title and
overwrites the rest, so a hand edit to the body does not survive.

A theme carrying fewer than two members is reported: below two, the notes should
just `Keywords` each other and the theme should be retired at VERIFY.

Run from the vault root in DREAM phase 7, before gen_hubs (which lists themes).
"""
import glob, os, re, sys
from _gen_util import write_if_changed, split_note, links_in, fm_block, stamp

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
STAMP = stamp()
WIKILINK = re.compile(r"\[\[([^\]|]+)")

def base(p):
    return os.path.splitext(os.path.basename(p))[0]

def title_of(txt, fallback):
    return next((l[2:].strip() for l in txt.splitlines() if l.startswith("# ")), fallback)

def main():
    theme_files = sorted(glob.glob(os.path.join(ROOT, "augment_wiki/theme/*.md")))
    themes = {base(f): f for f in theme_files}
    if not themes:
        print("no theme notes to regenerate")
        return

    members = {t: [] for t in themes}
    content = (glob.glob(os.path.join(ROOT, "augment_wiki/concept/*.md"))
               + glob.glob(os.path.join(ROOT, "augment_wiki/entity/*.md"))
               + glob.glob(os.path.join(ROOT, "augment_wiki/tension/*.md")))
    for f in content:
        txt = open(f, encoding="utf-8").read()
        fm, _ = split_note(txt)
        kws = links_in(fm.get("keywords"))
        if not kws:
            continue
        ti = title_of(txt, base(f))
        for tgt in kws:
            if tgt in members:
                members[tgt].append((base(f), ti))

    thin = []
    for t, f in themes.items():
        title = title_of(open(f, encoding="utf-8").read(), t)
        mem = sorted(members[t], key=lambda x: x[1].lower())
        if len(mem) < 2:
            thin.append(f"{t} ({len(mem)})")
        out = fm_block(generated_by='augment/gen_themes.py', generated_at=STAMP, type='"[[theme]]"', status='"#current"') + [f"# {title}", "",
               f"Topical anchor (CONTRACT §3). The {len(mem)} note(s) below point here "
               "through their `keywords:` list; this list is generated, do not edit by hand.",
               "", "## Notes", ""]
        out += [f"- [[{b}]]: {ti}" for b, ti in mem] or ["(none yet)"]
        out.append("")
        write_if_changed(f, "\n".join(out))

    print(f"regenerated {len(themes)} theme bodies: "
          + ", ".join(f"{t} ({len(members[t])})" for t in sorted(themes)))
    if thin:
        print(f"  advisory: under-populated themes (retire at VERIFY if they stay thin): {', '.join(thin)}")

if __name__ == "__main__":
    main()
