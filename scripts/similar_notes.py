#!/usr/bin/env python3
"""Which existing wiki notes a note about to be minted most resembles.

PROCESS step 6 and MINT ask whether a concept already exists under another name,
a judgement about conceptual identity that a literal grep cannot make: a search
for "under-occupation" misses a note titled "under-occupied". On 2026-09-17 that
let a near-duplicate of an existing note be minted and indexed, and only the
nightly convergence pass caught it afterwards, at 0.38 cosine, after it had
reached the history and the index. This runs the same TF-IDF cosine the
relations view uses (gen_relations.py's tokeniser and stopwords, over the same
note bodies), before the write rather than after it.

The candidate is scored against every concept, entity and tension note:

  >= 0.30  LIKELY SAME   read it before minting; extend it instead unless the
                         two genuinely make different claims
  >= 0.15  RELATED       worth reading; a likely link rather than a duplicate

Pass the drafted opening with the title: scored on its title alone, that same
near-duplicate rates 0.085, and with a two-sentence opening 0.468.

The numbers inform the existence check; they do not replace it. A low score
does not prove a concept is new, only that its wording is.

`--sources` is WRITE's check before a capture: the draft is also scored against
the source layer, so material the person already holds is found before a second
copy is filed. It reads only what the system may read: sources whose scope rule
puts them in scope and that are not `#excluded` (in frontmatter or in the index),
plus the inbox, where repeated captures land. Out-of-scope, unruled and other
ignored folders stay closed. Each hit is marked `wiki` or `source`.
Sources need their own cut-offs, since meeting minutes of one project share
most of their vocabulary. Measured on 2026-09-29 over 120 in-scope sources, each
scored against all the others: from 0.60 up the best match was almost always a
real duplicate (a sync-conflict copy, a `-AA-mdh` twin, a v2 beside its v3); from
0.30 to 0.60 it was a related but distinct note, such as the next meeting of the
same project. An exact copy of a note scores 0.99, a two-sentence paraphrase of it
0.45, and new material stays under 0.15. So a source hit reads

  >= 0.60  LIKELY SAME   read it before capturing; comment on it instead unless
                         the new material differs
  >= 0.30  RELATED       read the top one: a short paraphrase lands here

    python3 similar_notes.py <vault> --title "Candidate title" [--text-file draft.md | --text "..."] [--top 8] [--sources]
"""
import argparse, glob, importlib.util, json, math, os, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SAME, RELATED = 0.30, 0.15
SOURCE_SAME, SOURCE_RELATED = 0.60, 0.30


def _relations():
    """gen_relations.py's tokeniser and content reader, without running it."""
    argv, sys.argv = sys.argv, ["gen_relations.py", "."]
    try:
        spec = importlib.util.spec_from_file_location("gen_relations", os.path.join(HERE, "gen_relations.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.argv = argv
    return mod


def readable_sources(idx):
    """Source ids the system may read: in scope and not excluded, plus the inbox."""
    from _gen_util import load_config, scope_of, split_note, source_path
    cfg = load_config(".")
    root = str(cfg.get("source_root") or "").strip("/")
    inbox = (root + "/_inbox/") if root else "_inbox/"
    excluded = {e["id"] for e in idx if e.get("status") == "excluded"}
    out = []
    for p in sorted(glob.glob("**/*.md", recursive=True)):
        top = p.split("/")[0]
        if top.startswith(".") or top in ("augment_wiki", "augment_memory", "augment_plugin"):
            continue
        if p in excluded or not (p.startswith(inbox) or scope_of(p, cfg) == "in"):
            continue
        try:
            fm, _ = split_note(open(source_path(".", p), encoding="utf-8", errors="replace").read())
        except OSError:
            continue
        if "#excluded" in str(fm.get("augment", "")):
            continue
        out.append(p)
    return out


def source_text(sid):
    """A source's title and body for similarity, frontmatter dropped."""
    from _gen_util import source_path
    try:
        s = open(source_path(".", sid), encoding="utf-8", errors="replace").read()
    except OSError:
        return ""
    s = re.sub(r"^---\n.*?\n---\n", "", s, flags=re.S)
    return os.path.splitext(os.path.basename(sid))[0] + " " + s


def main():
    ap = argparse.ArgumentParser(description="Score a candidate note against the wiki before minting it.")
    ap.add_argument("vault")
    ap.add_argument("--title", required=True)
    ap.add_argument("--text", default="")
    ap.add_argument("--text-file")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--sources", action="store_true",
                    help="also score in-scope sources and the inbox (WRITE's pre-capture check)")
    a = ap.parse_args()
    os.chdir(a.vault)
    gr = _relations()
    body = a.text
    if a.text_file:
        body += "\n" + open(a.text_file, encoding="utf-8").read()
    idx = [json.loads(l) for l in open("augment_wiki/index.jsonl", encoding="utf-8") if l.strip()]
    notes = [e for e in idx if str(e.get("id", "")).startswith("augment_wiki/")
             and e.get("type") in ("concept", "entity", "tension") and os.path.exists(e["id"])]
    toks = {e["id"]: gr.tokens(gr.content(e["id"])) for e in notes}
    kind = {i: "wiki" for i in toks}
    if a.sources:
        for sid in readable_sources(idx):
            toks[sid] = gr.tokens(source_text(sid))
            kind[sid] = "source"
    # The title counts twice: in a new note it is the claim, and it is most of
    # what exists before the body is drafted.
    cand = gr.tokens((a.title + " ") * 2 + body)
    if not cand:
        print("SIMILAR: nothing to score (the title and text hold no content words)"); return
    df = Counter()
    for tl in list(toks.values()) + [cand]:
        df.update(set(tl))
    n = len(toks) + 1
    idf = {t: math.log((1 + n) / (1 + d)) + 1 for t, d in df.items()}

    def vec(tl):
        tf = Counter(tl)
        v = {t: tf[t] / len(tl) * idf[t] for t in tf}
        norm = math.sqrt(sum(w * w for w in v.values())) or 1.0
        return {t: w / norm for t, w in v.items()}

    cv = vec(cand)
    titles = {e["id"]: e.get("title", "") for e in notes}
    scored = sorted(((sum(w * vec(tl).get(t, 0.0) for t, w in cv.items()), i)
                     for i, tl in toks.items() if tl), reverse=True)[:a.top]
    n_src = sum(1 for k in kind.values() if k == "source")
    print(f"SIMILAR to \"{a.title}\" ({len(notes)} notes" + (f", {n_src} sources" if a.sources else "") + " scored):")
    same_hit = False
    for s, i in scored:
        same, related = (SOURCE_SAME, SOURCE_RELATED) if kind[i] == "source" else (SAME, RELATED)
        label = "LIKELY SAME" if s >= same else "RELATED" if s >= related else "weak"
        same_hit |= s >= same
        if not a.sources:
            print(f"  {s:.3f}  {label:11}  {os.path.splitext(os.path.basename(i))[0]}  ({titles[i]})")
        elif kind[i] == "wiki":
            print(f"  {s:.3f}  {label:11}  wiki    {i}  ({titles[i]})")
        else:
            print(f"  {s:.3f}  {label:11}  source  {i}")
    if same_hit and not a.sources:
        print("Read the LIKELY SAME note(s) before minting; extend instead unless the claims differ.")
    elif same_hit:
        print("Read the LIKELY SAME item(s) before capturing: comment on an existing source instead, "
              "or confirm with the person that the new material differs.")


if __name__ == "__main__":
    main()
