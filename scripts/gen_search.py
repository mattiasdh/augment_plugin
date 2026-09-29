#!/usr/bin/env python3
"""Write `augment_wiki/search.json`, the index a search reads without opening notes.

`index.jsonl` carries a wiki note's title and nothing a searcher types in another
language, so a search that cannot open files, the connector's `vault_search` on the
web and the phone above all, found a note only by its English title. This projects
what a search needs into one file: for every content note its title, type, kind,
status, aliases, keyword slugs, the first sentence of its body and the sources it
cites; for every processed source in scope, the wiki notes that cite it.

Sources are listed only where the vault's own scope rules put them in scope and
the index does not mark them excluded, the same rule the connector applies at read
time, so nothing a search could not open is named here either. Each entry also
carries its words already tokenised (`w`, a note's words with their weight: title
and aliases 3, keywords 2, summary 1; `d`, a note's title and alias words, for the
duplicate check; `t` and `n`, a source's path and file-name words), with the
tokeniser the connector's parity tests pin to its own: the Worker may spend 10 ms
of CPU a request, and tokenising the whole index there took twice that. Derived and
overwritten on every run, written only when its content changed, never hand-edited.
DREAM phase 7 runs it with the other generators.

    python3 gen_search.py <vault>
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gen_util import load_config, scope_of, split_note, links_in
from _memory import tokens

CONTENT = ("concept", "entity", "tension", "theme")
SUMMARY_MAX = 200


def first_sentence(body):
    """The opening sentence of a note's prose, markdown stripped, at most SUMMARY_MAX characters."""
    lines = [l for l in body.splitlines() if l.strip() and not l.startswith("#") and not l.startswith(">")]
    text = re.sub(r"\[\[([^\]|]+\|)?([^\]]+)\]\]", r"\2", " ".join(lines[:3]))
    text = re.sub(r"[*_`]", "", text)
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    s = (m.group(1) if m else text).strip()
    return s if len(s) <= SUMMARY_MAX else s[:SUMMARY_MAX - 1].rstrip() + "…"


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    idx = [json.loads(l) for l in open(os.path.join(root, "augment_wiki/index.jsonl"), encoding="utf-8") if l.strip()]
    cfg = load_config(root)
    notes, sources = [], []
    for e in idx:
        i = str(e.get("id", ""))
        if i.startswith("augment_wiki/") and e.get("type") in CONTENT:
            p = os.path.join(root, i)
            if not os.path.exists(p):
                continue
            fm, body = split_note(open(p, encoding="utf-8").read())
            title = e.get("title") or next((l[2:].strip() for l in body.splitlines() if l.startswith("# ")), "")
            al = fm.get("aliases") if isinstance(fm.get("aliases"), list) else []
            kw, summary = links_in(fm.get("keywords")), first_sentence(body)
            named = tokens(f"{title} {os.path.basename(i)}") | tokens(" ".join(str(x) for x in al))
            w = {t: 1 for t in tokens(summary)}
            w.update({t: 2 for t in tokens(" ".join(kw))})
            w.update({t: 3 for t in named})
            notes.append({
                "id": i, "title": title, "type": e.get("type"), "kind": e.get("kind"),
                "status": e.get("status"), "aliases": [str(x) for x in al],
                "keywords": kw, "summary": summary,
                "sources": [c.get("source") for c in e.get("compiled_from") or [] if isinstance(c, dict)],
                "w": dict(sorted(w.items())), "d": sorted(named),
            })
        elif (not i.startswith("augment_wiki/") and e.get("status") == "processed"
              and not e.get("renamed_to") and scope_of(i, cfg) == "in"):
            sources.append({"id": i, "cited_by": list(e.get("produced") or []),
                            "t": sorted(tokens(i[:-3] if i.endswith(".md") else i)),
                            "n": sorted(tokens(os.path.splitext(os.path.basename(i))[0]))})
    notes.sort(key=lambda n: n["id"])
    sources.sort(key=lambda s: s["id"])
    text = json.dumps({"schema": 2, "notes": notes, "sources": sources},
                      ensure_ascii=False, separators=(",", ":")) + "\n"
    out = os.path.join(root, "augment_wiki/search.json")
    old = open(out, encoding="utf-8").read() if os.path.exists(out) else None
    if old != text:
        with open(out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    with_aliases = sum(1 for n in notes if n["aliases"])
    print(f"search: {len(notes)} notes ({with_aliases} with aliases), {len(sources)} sources, "
          f"{len(text) // 1024} KB; {'written' if old != text else 'unchanged'}")


if __name__ == "__main__":
    main()
