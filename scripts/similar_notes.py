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

    python3 similar_notes.py <vault> --title "Candidate title" [--text-file draft.md | --text "..."] [--top 8]
"""
import argparse, importlib.util, json, math, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
SAME, RELATED = 0.30, 0.15


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


def main():
    ap = argparse.ArgumentParser(description="Score a candidate note against the wiki before minting it.")
    ap.add_argument("vault")
    ap.add_argument("--title", required=True)
    ap.add_argument("--text", default="")
    ap.add_argument("--text-file")
    ap.add_argument("--top", type=int, default=8)
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
    print(f"SIMILAR to \"{a.title}\" ({len(notes)} notes scored):")
    for s, i in scored:
        label = "LIKELY SAME" if s >= SAME else "RELATED" if s >= RELATED else "weak"
        print(f"  {s:.3f}  {label:11}  {os.path.splitext(os.path.basename(i))[0]}  ({titles[i]})")
    if scored and scored[0][0] >= SAME:
        print("Read the LIKELY SAME note(s) before minting; extend instead unless the claims differ.")


if __name__ == "__main__":
    main()
