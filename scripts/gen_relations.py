#!/usr/bin/env python3
"""Regenerate augment_wiki/view/relations.md, the relationship overlay (CONTRACT §12).

Convergent lane: unlinked note pairs ranked by CONTENT similarity, a TF-IDF
cosine over the note bodies, so candidates reflect what the notes actually say
and not only whether they happen to share a source. Co-citation, shared link
neighbours and shared Kind are secondary boosters that break ties and lift a
content match that is also structurally corroborated. Deterministic and
reproducible: a fixed tokeniser and stopword list, no model call and no
embeddings, so the overlay is identical run to run. It only proposes; at VERIFY the
model judges the shortlist and a confirmed pair becomes an unsourced `Keywords`
tag (CONTRACT §7), or a sourced `## Links` relationship where a source states the
connection. Pairs already tagged in a note's `keywords:` list are excluded.

Decay lane: the inverse of the convergent lane. Existing `Keywords` edges on notes
recompiled today whose two notes now share almost no content, proposed for REMOVAL
at VERIFY. Scoped to recompiled notes because a source rewrite is what makes an edge
worth re-testing.

Divergent lane: existing `contradicts` edges, as standing tension candidates.

Untested-consensus lane: the inverse of divergent, anchors whose members
converge yet carry no `contradicts` edge, a one-sided consensus surfaced for a
DISCUSS pass (COGNITION §1, augmentation). Advisory only; never gates.

Run from the vault root in DREAM phase 7.

## How the ranking is computed

This is the authoritative description of the mechanism. CONTRACT §12 fixes what
the view may *do* (it proposes, never writes; a promotion reaches a note only at
VERIFY); it deliberately does not fix *how* it ranks, because these are tuned
numbers and a contract amended to change a weight would soon stop being true.

**Similarity.** A TF-IDF cosine over the note bodies, frontmatter (and with it the
`sources:` citation list) and the `Source:` lines stripped, so the ranking reflects
what notes say rather than what they cite.
The cosine leads: co-citation (x0.04, capped at 3), shared link neighbours (x0.02,
capped at 3) and a shared `Kind` (x0.02) are boosters capped so they only break
ties. A pair with real content overlap therefore always outranks one held up by
co-citation alone, which is what stops the net manufacturing a top candidate out
of shared sources the way a structure-only measure did.

**Saturation** (`SAT`). The combined score is damped by the pair's mean degree
against the most-linked note, so two already heavily-linked notes yield a little
rank to an equally similar pair reaching an under-linked one. Without it the
harvest kept reconditioning the same dense core.

**Two lanes.** The convergent ranking is the global top by adjusted score
(`TOP`, `FLOOR`). The coverage list adds each note's own strongest unlinked tie
that the ranking missed (`COVERAGE_FLOOR`), so a peripheral note gets one
candidate judged instead of staying permanently below the cut.

**Membership** is each note scored against the TF-IDF centroid of an anchor's
current members (`MB_FLOOR`, `MB_TOP`). An anchor is any node two or more notes
already keyword-tag, so membership is general across types, not theme-only.

**Decay** re-scores a recompiled note's existing keyword edges and lists those now
below `DECAY_FLOOR`, half the proposal floor: creating an edge and destroying one
are not symmetric, so removing a confirmed connection needs the stronger evidence.
The sidecar carries the answer either way, `ruling: keep` for a declined removal and
no ruling for a declined promotion, which are opposite answers about the same pair.

**Its one failure mode is a recall gap, never a wrong link.** The cosine orders
what gets read first; it never decides anything. So the model judging the slice is
not confined to it and may raise a pair the ranking buried. Embedding similarity
would add recall but is model-version-dependent and non-reproducible, so it may
only ever feed this advisory view, clearly marked, never the sourced graph.
"""
import datetime, glob, json, math, os, re, sys
from _gen_util import write_if_changed, read_note, split_note, links_in, fm_block, stamp
from collections import Counter, defaultdict
from itertools import combinations

_args = [a for a in sys.argv[1:] if not a.startswith("--")]
ROOT = _args[0] if _args else "."
# `--status` answers "is a fresh slice owed right now?" in one call, the shape
# DREAM phase 4b already uses for `restyle_queue.py . status`. It computes the net
# (the standing backlog) and separately checks verify-queue.md's curated tail for
# an outstanding CV-/MB-/SL- id (a batch already presented and not yet answered),
# since these are different questions with different answers: the net is non-empty
# by construction until fully drained, while an outstanding batch is what the
# pacing rule actually gates on. Conflating them is what stalled the pass twice in
# two days: once by reading "did anything change" for "is anything owed"
# (CHANGELOG 2026-08-25), then by reading "the net has un-judged pairs" for "a
# batch is outstanding" (CHANGELOG 2026-08-26), which can never be false once the
# first fix made the net's true size visible. Writes nothing; the view is
# untouched by this flag.
STATUS = "--status" in sys.argv[1:]
# Answers "what is the full priority lane, unabridged" for DREAM phase 6 to draw
# its slice from once the lane runs deeper than PRIO_TOP (the display cap on
# relations.md's own Priority section, kept low there for a readable preview).
# Before this flag existed, reading the full lane meant importing the module and
# raising PRIO_TOP in memory, a workaround rather than a supported path (VERIFY,
# 2026-08-28). The view is untouched by this flag, same as --status; the one
# thing it does write is `augment_wiki/priority-lane.json`, the day's pinned lane
# (see the flag's own block below), which is tooling state like the dismissal
# sidecar and stays out of index.jsonl and history.jsonl.
PRIORITY_LIST = "--priority-list" in sys.argv[1:]
# The nightly anchoring pass: which anchors do the notes *this cycle wrote* belong to.
# Narrower than the priority lane on purpose, and the one candidate set DREAM applies
# without asking (CONTRACT §12), because attaching a new note to what it is about is
# the cheapest, most reversible write in the system and the one whose absence was
# costing the most: an unanchored note stays unfindable until it happens to rank.
ANCHOR_LIST = "--anchor-list" in sys.argv[1:]
IDX = os.path.join(ROOT, "augment_wiki/index.jsonl")
STAMP = stamp()
TODAY = datetime.date.today().isoformat()
TOP = 60        # cap on convergent candidates shown
FLOOR = 0.08    # minimum combined score to be a candidate
# A note compiled within this window is "recently compiled", and its candidates are
# drawn before the standing backlog's (DREAM phase 6). The window is a plain recency
# rule rather than a mark carried per note: a candidate touching a note the person has
# just had processed is the one they hold context for, and the one whose adjacencies
# nobody has yet had the chance to judge. Seven days is wide enough to survive a few
# skipped nightly runs; anything older is not lost, it falls back to the ordinary
# convergent and coverage lanes below.
FRESH_DAYS = 7
# Cap on priority candidates listed. A single well-connected fresh note (a project
# entity, say) can carry dozens of pairs and membership hits, so the lane needs its
# own cut the way the convergent lane does; the count above the list stays whole.
PRIO_TOP = 30

# Function words across the vault's three languages (EN/FR/NL); fixed for reproducibility.
STOP = set((
    "the a an and or of to in on for with as is are was were be been being by at it its this that these those from "
    "into over under not no nor but if then than so such can could may might will would should must have has had do "
    "does did their there here they them his her our your out about which who whom what when where why how all any "
    "each more most other some only own same too very also both few "
    "de la le les un une des du et ou a au aux en dans sur pour par avec est sont etre ce cette ces qui que ne pas "
    "plus se son sa ses leur leurs nous vous ils elles on comme mais donc ainsi entre chaque tout tous toute toutes "
    "het de een van en op te met voor als is zijn wordt worden dat die deze niet ook naar aan bij uit door om over "
    "maar want dus zoals tussen elke alle deze hun hij zij wij "
).split())

LINK = re.compile(r"^-\s+(related|example_of|contradicts)\s+\[\[([^\]|]+)")
KEYWORDS = re.compile(r"^Keywords:\s*(.*)$")
WIKILINK = re.compile(r"\[\[([^\]|]+)")

def base(i):
    return os.path.splitext(os.path.basename(i))[0]

def tokens(text):
    return [t for t in re.findall(r"[a-zà-ÿ0-9]+", text.lower()) if len(t) >= 3 and t not in STOP]

def content(path):
    """Note text for similarity: title + prose + link reasons, minus metadata and citations."""
    try:
        s = open(os.path.join(ROOT, path), encoding="utf-8").read()
    except FileNotFoundError:
        return ""
    s = re.sub(r"^---\n.*?\n---\n", "", s, flags=re.S)  # drop frontmatter
    # The citation list is `sources:` frontmatter since the OKF alignment, so dropping
    # the frontmatter already removes it and no `## Sources` skip is needed. The
    # `Source:` lines inside `## Links` still are: they are filenames, which are noise
    # in a similarity measure, while the `Why:` lines above them are real content.
    out = [line for line in s.splitlines() if not line.strip().startswith("Source:")]
    return " ".join(out)

def parse_links(path):
    fm, body = read_note(os.path.join(ROOT, path))
    if not body:
        return set(), set()
    lines = body.splitlines()
    targets, contra, in_block = set(), set(), False
    targets.update(links_in(fm.get("keywords")))   # already promoted -> exclude the pair
    for ln in lines:
        s = ln.strip()
        if s.startswith("## Position") and "[[" in s:   # a tension note links its two positions through itself
            for t in WIKILINK.findall(s):
                targets.add(t.strip())
        if s == "## Links":
            in_block = True; continue
        if in_block and s.startswith("## ") and s != "## Links":
            break
        if in_block:
            m = LINK.match(s)
            if m:
                t = m.group(2).strip(); targets.add(t)
                if m.group(1) == "contradicts":
                    contra.add(t)
    return targets, contra


QUEUE_ITEM = re.compile(r"(?m)^\s*(?:\d+\.|[-*+])\s.*?\b((?:CV|MB|SL)-\d{4}-\d{2}-\d{2}-\d+)\b")
QUEUE_SLUG = re.compile(r"`([a-z0-9][a-z0-9-]*)`")


def read_queue_pending(root, valid):
    """Outstanding ids and the note-pairs they name, from verify-queue.md's curated tail.

    A proposal already sitting in the queue, waiting on the person's answer, is not
    new material: the id extraction is `--status`'s own (CONTRACT §12's outstanding-
    batch gate), reused here rather than re-derived, so the two readings of the same
    file cannot fall out of step. The per-line slug pairing is additional: an id says
    a batch is open, not which candidate it covers, and a person working the priority
    lane by hand needs the second thing to recognise a pair already in front of them
    (found 2026-09-12: the lane's own top five duplicated four still-open items and
    had to be caught by inspection). A line naming other than exactly two known slugs
    is skipped rather than guessed at, since a membership or a multi-note line has no
    single pair to record.
    """
    qpath = os.path.join(root, "augment_wiki/verify-queue.md")
    qtext = open(qpath, encoding="utf-8").read() if os.path.exists(qpath) else ""
    m = re.search(r"(?m)^## Queued for confirmation\s*$", qtext)
    tail = qtext[m.end():] if m else qtext
    # Scoped to the live-items span only: up to the next top-level heading, never
    # into "## System observations" or "## Previous run (log)" below it. Those
    # sections narrate resolved history and can cite a past id in prose (found
    # 2026-09-12: a struck System-observations bullet naming a batch closed two
    # days earlier tripped this same gate, reporting a batch outstanding that had
    # none), which is exactly the false positive the numbered/bulleted-line
    # requirement already exists to rule out for the live section itself.
    nxt = re.search(r"(?m)^## ", tail)
    if nxt:
        tail = tail[:nxt.start()]
    outstanding = sorted(set(mm.group(1) for mm in QUEUE_ITEM.finditer(tail)))
    pending_pairs = {}
    for line in tail.splitlines():
        idm = QUEUE_ITEM.match(line)
        if not idm:
            continue
        slugs = [s for s in dict.fromkeys(QUEUE_SLUG.findall(line)) if s in valid]
        if len(slugs) == 2:
            pending_pairs[frozenset(slugs)] = idm.group(1)
    return outstanding, pending_pairs


def main():
    idx = [json.loads(l) for l in open(IDX, encoding="utf-8") if l.strip()]
    notes = [e for e in idx if str(e.get("id", "")).startswith("augment_wiki/")
             and e.get("type") in ("concept", "entity", "tension")]
    valid = {base(e["id"]) for e in notes}
    kind = {base(e["id"]): e.get("kind") for e in notes}

    # TF-IDF vectors over note content
    toks = {base(e["id"]): tokens(content(e["id"])) for e in notes}
    Ndoc = len(toks)
    df = Counter()
    for tl in toks.values():
        for t in set(tl):
            df[t] += 1
    idf = {t: math.log((1 + Ndoc) / (1 + d)) + 1 for t, d in df.items()}
    vec = {}
    for b, tl in toks.items():
        if not tl:
            vec[b] = {}; continue
        tf = Counter(tl)
        v = {t: (tf[t] / len(tl)) * idf[t] for t in tf}
        norm = math.sqrt(sum(w * w for w in v.values())) or 1.0
        vec[b] = {t: w / norm for t, w in v.items()}
    def cos(a, b):
        va, vb = vec[a], vec[b]
        if len(va) > len(vb):
            va, vb = vb, va
        return sum(w * vb.get(t, 0.0) for t, w in va.items())

    # structural signals
    cites = defaultdict(set)
    for e in notes:
        for cf in e.get("compiled_from", []):
            src = cf.get("source") if isinstance(cf, dict) else cf
            if src:
                cites[src].add(base(e["id"]))
    links, contra_edges = {}, set()
    for e in notes:
        b = base(e["id"]); tg, co = parse_links(e["id"])
        links[b] = {t for t in tg if t in valid}
        for t in co:
            if t in valid:
                contra_edges.add(tuple(sorted((b, t))))
    linked = set()
    for a, ts in links.items():
        for t in ts:
            linked.add(tuple(sorted((a, t))))

    # Degree per note (sourced links + Keywords tags), for the saturation down-weight
    # and the coverage lane. `keywords_of` is defined here so both the candidate scoring
    # and the membership pass below can use it.
    path_of = {base(e["id"]): e["id"] for e in notes}
    def keywords_of(b):
        try:
            fm, _ = read_note(os.path.join(ROOT, path_of[b]))
        except KeyError:
            return set()
        return set(links_in(fm.get("keywords")))
    deg = {b: len(links.get(b, set())) + len(keywords_of(b)) for b in valid}
    maxdeg = max(deg.values()) if deg else 1
    SAT = 0.10          # saturation down-weight: a pair of two maximally-linked notes loses this much
    COVERAGE_FLOOR = 0.05

    shared_src = defaultdict(int)
    for members in cites.values():
        for a, b in combinations(sorted(members), 2):
            shared_src[(a, b)] += 1

    # VERIFY dismissals: a pair the person looked at and declined, persisted in a sidecar
    # (relations_dismissed.jsonl) so it never resurfaces in the candidate net. Kept out of
    # index.jsonl and history.jsonl deliberately: this is tooling state, not vault state.
    # A line carries an optional `ruling`: absent or "no-link" means the person
    # declined to *create* the edge (excluded from the candidate net below); "keep"
    # means they declined to *remove* an existing one (excluded from the decay lane).
    # The two are opposite answers about the same pair and must not cancel each other.
    dismissed, kept = set(), set()
    dpath = os.path.join(ROOT, "augment_wiki/relations_dismissed.jsonl")
    if os.path.exists(dpath):
        for l in open(dpath, encoding="utf-8"):
            l = l.strip()
            if not l:
                continue
            rec = json.loads(l)
            pr = rec.get("pair")
            if pr and len(pr) == 2:
                (kept if rec.get("ruling") == "keep" else dismissed).add(tuple(sorted(pr)))

    # Subsumption (CONTRACT §7, the ladder). A pair is not proposed where an
    # existing relation already carries the same claim. The test is deliberately
    # *not* "does a path exist": that would be first-come-first-served, letting
    # whichever relation happened to be written first suppress a stronger direct
    # tie, and making the graph depend on processing order rather than on what the
    # sources say. Two clauses, and each names why the existing relation is the
    # better carrier rather than merely the earlier one.
    #
    # Clause A, authorship. A `kind: person` entity and a note joined to it through
    # any non-theme note: the person note exists to name an author, their model does
    # the connecting, and a tag from the note to the author is a second path to a
    # place the graph already reaches. `barbara-minto` reaches `autonomous-deck`
    # through `minto-pyramid-principle`, `johan-rockstrom` reaches `un-sustainable-
    # development-goals` through `sdg-wedding-cake`. This clause is about the nature
    # of one endpoint, so it holds however well-connected the carrier is: measured
    # 2026-09-12, 92 of its 110 pairs run through carriers of degree 7 to 18
    # (`storytelling` at 10, a project's own reversibility framework at 16), which
    # is why a degree cap cannot replace it.
    #
    # Clause B, specificity. Any pair joined through a carrier of degree six or
    # fewer, counting both sourced `## Links` and `Keywords` tags, because a note
    # that gathers few things says something specific about the ones it gathers.
    # A loose anchor says nothing and suppresses nothing: `renovation` (degree 28),
    # `sufficiency` (22) and `gro` (14) are all above the cap by construction, so a
    # strong pair sharing only a broad topic still competes.
    #
    # Both caps were measured against the live net before being written, the broad
    # forms having been refuted twice: excluding every pair with a shared sourced-
    # link neighbour took 104 of 136 displayed candidates (76%), and excluding every
    # pair sharing any Keywords anchor took 67% of the displayed lane. The two
    # clauses together take 262 of 13,106 pool pairs (2.0%), about 10% of what the
    # lane actually displays.
    CARRIER_SPECIFIC = 6
    person_notes = {base(e["id"]) for e in notes
                    if re.sub(r'[\[\]"]', "", str(e.get("kind", ""))).strip() == "person"}
    theme_notes = {base(e["id"]) for e in notes if e.get("type") == "theme"}
    undirected = defaultdict(set)
    for _a, _ts in links.items():
        for _t in _ts:
            undirected[_a].add(_t)
            undirected[_t].add(_a)
    # The carrier graph is the union of both relationship tiers: a note carries a
    # pair whether it joins them by a sourced Link or by a Keywords tag, and its
    # degree counts both, so "specific" means specific in the graph the reader
    # actually navigates rather than in one tier of it.
    theme_slugs = {os.path.splitext(os.path.basename(f))[0]
                   for f in glob.glob(os.path.join(ROOT, "augment_wiki/theme/*.md"))}
    carrier = defaultdict(set)
    for _a, _ts in links.items():
        for _t in _ts:
            carrier[_a].add(_t)
            carrier[_t].add(_a)
    for _b in valid:
        for _t in keywords_of(_b):
            if _t in valid | theme_slugs:
                carrier[_b].add(_t)
                carrier[_t].add(_b)
    carrier_deg = {z: len(v) for z, v in carrier.items()}

    # Keywords-anchor membership. An anchor is any node two or more notes already
    # keyword-tag (CONTRACT §12): a theme, or a concept/entity acting as a
    # gathering point. Computed here (clause C needs it) rather than where the
    # membership lane used to compute it a second time further down, which still
    # reads `anchors` and `members` unchanged. An anchor's *membership* (how many
    # notes keyword-tag it) is a narrower count than its carrier degree above:
    # carrier degree also counts the anchor's own outward ties and any sourced
    # Links, which is why `gro` (6 members) sits at a carrier degree past
    # `CARRIER_SPECIFIC` and clause B does not reach it.
    anchors = valid | theme_slugs
    members = defaultdict(set)
    for _b in valid:
        for _t in keywords_of(_b):
            if _t in anchors:
                members[_t].add(_b)

    # Clause C, small shared anchor. Two notes tagged to the same Keywords anchor
    # of four or fewer members are subsumed: a small anchor is close to redundant
    # with the anchor tag itself, since almost nothing else is gathered there to
    # distinguish the pair from any other two members. Measured 2026-09-10/11:
    # excluding *any* shared Keywords anchor took 67% of the displayed lane,
    # dominated by large, loose anchors (`renovation` at 28 members, `sufficiency`
    # at 22) that say almost nothing on their own; capped at four members it takes
    # 3.3 to 8.2%, and every anchor-size-two example read as genuine redundancy
    # rather than a missed finding. Person's decision, 2026-09-12.
    KEYWORD_ANCHOR_SPECIFIC = 4

    def subsumed(a, b):
        if (a in person_notes or b in person_notes) and (undirected[a] & undirected[b]) - theme_notes:
            return True                                    # clause A, authorship
        if any(carrier_deg.get(z, 10 ** 6) <= CARRIER_SPECIFIC
               for z in carrier[a] & carrier[b]):
            return True                                    # clause B, specificity
        return any(len(members.get(z, ())) <= KEYWORD_ANCHOR_SPECIFIC
                   for z in keywords_of(a) & keywords_of(b) & anchors)  # clause C

    # Two-lane candidate net. The similarity lane ranks pairs by adjusted score:
    # the combined content-plus-booster score, damped by a saturation term so a
    # pair of two already heavily-linked notes is nudged below an equally similar
    # pair that would connect an under-linked note. The coverage lane then picks up
    # each note's single strongest unlinked tie that the similarity top missed, so
    # a peripheral note gets one candidate judged at VERIFY even when its best pair
    # never rises into the global top. Widens promotion past the same dense core
    # (60% coverage / 40% similarity in a DREAM cycle, DREAM phase 6).
    cands, best = [], {}
    for a, b in combinations(sorted(valid), 2):
        pair = (a, b)
        if pair in linked or pair in contra_edges or pair in dismissed \
                or subsumed(a, b):
            continue
        ss = shared_src.get(pair, 0)
        neigh = len(links.get(a, set()) & links.get(b, set()))
        # Structural noise filter (VERIFY, 2026-08-27): a project/project or
        # project/organisation pair with no shared source and no shared link
        # neighbor is the systematic proximity pattern VERIFY has declined dozens
        # of times as a class ("two unrelated projects, no stated connection";
        # "systematic authorship signal"), never once approved. Cosine similarity
        # alone on this pairing is near-guaranteed noise (shared practice/project
        # vocabulary, not a real tie), so it is excluded from the net outright
        # rather than surfaced and declined again at VERIFY. A pair with at least
        # one structural corroborator (ss or neigh > 0) still competes normally;
        # only the zero-corroboration case is filtered.
        ka, kb = kind.get(a), kind.get(b)
        noise_pair = "project" in (ka, kb) and {ka, kb} <= {"project", "organisation"}
        if noise_pair and ss == 0 and neigh == 0:
            continue
        c = cos(a, b)
        sk = 1 if kind.get(a) and kind.get(a) == kind.get(b) else 0
        score = c + 0.04 * min(ss, 3) + 0.02 * min(neigh, 3) + 0.02 * sk
        sat = (deg.get(a, 0) + deg.get(b, 0)) / (2 * maxdeg)
        adj = score * (1 - SAT * sat)
        for x, y in ((a, b), (b, a)):          # each note's own strongest tie, for coverage
            if x not in best or adj > best[x][0]:
                best[x] = (adj, y, c)
        if score >= FLOOR:
            cands.append((round(adj, 4), round(score, 4), round(c, 3), ss, neigh, sk, a, b))
    cands.sort(key=lambda x: (-x[0], x[6], x[7]))

    # Coverage lane: each note's strongest unlinked tie that the similarity top did
    # not already surface. Keeps a peripheral note from staying invisible when its
    # best pair sits below the global cut. One per note, deduplicated, cosine floor.
    shown = {tuple(sorted((r[6], r[7]))) for r in cands[:TOP]}
    coverage, seen = [], set()
    for x, (adj, y, c) in best.items():
        pair = tuple(sorted((x, y)))
        if pair in shown or pair in seen or c < COVERAGE_FLOOR:
            continue
        seen.add(pair)
        coverage.append((round(adj, 4), round(c, 3), pair[0], pair[1]))
    coverage.sort(key=lambda r: (-r[0], r[2], r[3]))

    # Membership is general, not theme-only: `anchors` and `members` are computed
    # above, alongside clause C, which needs the same anchor-membership count.
    # For each anchor, propose more notes by content match to its members' centroid.

    # Oversized anchors (CONTRACT §7, rung 2). An anchor that has grown large *and*
    # whose members hang together is the signal that a node is missing: the notes
    # are gathering around something nobody has written yet, or around a content
    # note quietly doing double duty as a claim and as a gathering point. Size alone
    # does not say this, and the density test is what separates the two shapes.
    # Measured over all 53 anchors of three or more members on 2026-09-12: a
    # *star* gathers notes that have nothing to do with each other and stays sparse
    # (a project entity at 13 members scores 0.090, the practice's own organisation
    # entity 0.107, a broad principle 0.095), where a *cluster* is where the missing
    # concept lives (a standard at 10 members scores 0.333, a model at 10 scores
    # 0.200). The six existing themes sit between 0.121 and 0.187, which is where
    # the floor comes from: it is the density the notes themselves have shown a real
    # topic to have, not a number chosen in advance.
    #
    # Reported, never applied, and only where the membership lane is *also*
    # proposing a new tag into that anchor: the moment a cluster is about to grow is
    # when the question is worth asking, and gating on it throttles the report to a
    # handful a cycle instead of re-stating thirteen standing anchors every night.
    OVERSIZED_MIN = 7
    OVERSIZED_DENSITY = 0.12

    def anchor_density(mem):
        """How densely an anchor's members keyword-tag each other, ignoring the anchor."""
        mem = sorted(mem)
        if len(mem) < 2:
            return 0.0
        edges = 0
        for i, a in enumerate(mem):
            ka = keywords_of(a)
            for b in mem[i + 1:]:
                if b in ka or a in keywords_of(b):
                    edges += 1
        return edges / (len(mem) * (len(mem) - 1) / 2)

    # Themes are excluded: a theme growing is a theme working, and the concept it
    # gathers is not missing, it is the theme. What this looks for is the opposite
    # case, a *content* note (a method, a standard, a principle, a model) that has
    # quietly taken on anchor duty alongside the claim it was written to make. Eight
    # of them carried seven or more members on 2026-09-12, a standard at 10 and a
    # principle at 10 among them, and nothing in the system had ever said so.
    oversized = {}
    for t, mem in members.items():
        if t in theme_slugs or len(mem) < OVERSIZED_MIN:
            continue
        d = anchor_density(mem)
        if d >= OVERSIZED_DENSITY:
            oversized[t] = (len(mem), round(d, 3))

    def centroid(mem):
        acc = defaultdict(float)
        for m in mem:
            for tok, w in vec.get(m, {}).items():
                acc[tok] += w
        n = math.sqrt(sum(w * w for w in acc.values())) or 1.0
        return {tok: w / n for tok, w in acc.items()}

    MB_FLOOR, MB_TOP = 0.12, 8
    memb_props = {}
    for t, mem in members.items():
        if len(mem) < 2:
            continue                       # need a profile to match against
        cen = centroid(mem)
        # A candidate already joined to the anchor structurally, by a sourced Links
        # relationship, a contradicts edge, or a sidecar dismissal, is excluded the
        # same way the pair lane above excludes it (CONTRACT §12: "two candidates
        # never enter the net at all"). Missing here let an already-linked or
        # already-declined pair resurface as a membership candidate (2026-08-31),
        # since this loop scored every valid note against the centroid with no
        # structural filter of its own.
        scored = sorted(
            ((round(sum(w * cen.get(tok, 0.0) for tok, w in vec.get(b, {}).items()), 3), b)
             for b in valid if b not in mem and b != t
             and tuple(sorted((t, b))) not in linked | contra_edges | dismissed
             and not subsumed(t, b)),
            reverse=True)
        hits = [(s, b) for s, b in scored if s >= MB_FLOOR][:MB_TOP]
        if hits:
            memb_props[t] = hits

    # Priority lane: every candidate touching a note compiled inside the FRESH_DAYS
    # window, drawn from the lanes already computed rather than scored separately, so
    # a pair appears here and in its home lane with the same number behind it. This
    # exists because the ranking alone buries exactly the candidates most worth
    # judging: a note compiled today enters a net of hundreds and sorts on cosine like
    # any other, so the adjacencies of freshly processed material queue behind a
    # backlog that can take many sweeps to drain, and are read cold weeks later
    # instead of while the person still has the source in mind. Ordered by score
    # within the lane, pairs before memberships.
    fresh_cutoff = (datetime.date.today() - datetime.timedelta(days=FRESH_DAYS)).isoformat()
    fresh_notes = {base(e["id"]) for e in notes
                   if str(e.get("compiled", "")) >= fresh_cutoff} & valid
    prio_pairs, prio_seen = [], set()
    for adj, score, c, ss, neigh, sk, a, b in cands:
        if a in fresh_notes or b in fresh_notes:
            prio_pairs.append((adj, c, a, b, "convergent"))
            prio_seen.add((a, b))
    # The coverage lane floors on cosine alone (`COVERAGE_FLOOR`, 0.05) so that a
    # peripheral note gets one candidate judged even when its best tie is weak. That
    # is right for the backlog and wrong for the priority lane, which decides what is
    # read *first*: recency should order the queue, not lower the bar it has to clear.
    # A coverage candidate is therefore promoted into the priority lane only if it
    # also cleared the convergent lane's own floor. Measured 2026-09-12: 6 of 100
    # priority pairs came in below it, the weakest at 0.054 pairing a client entity
    # with an unrelated political-theory note, and those six are the shape
    # that consumed roughly forty judgements for zero approvals across 2026-09-05 to
    # 2026-09-07 (INCIDENTS, 2026-09-09).
    floored = {tuple(sorted((r[6], r[7]))) for r in cands}
    for adj, c, a, b in coverage:
        if (a, b) not in prio_seen and (a in fresh_notes or b in fresh_notes) \
                and tuple(sorted((a, b))) in floored:
            prio_pairs.append((adj, c, a, b, "coverage"))
            prio_seen.add((a, b))
    prio_pairs.sort(key=lambda r: (-r[0], r[2], r[3]))
    prio_memb = []
    for t in sorted(memb_props):
        for s, b in memb_props[t]:
            if b in fresh_notes or t in fresh_notes:
                prio_memb.append((s, b, t))
    prio_memb.sort(key=lambda r: (-r[0], r[1], r[2]))
    priority_n = len(prio_pairs) + len(prio_memb)

    if ANCHOR_LIST:
        # The nightly anchoring pass (DREAM phase 6). Scoped to notes this cycle
        # actually wrote, not the seven-day freshness window the priority lane uses:
        # a note is anchored the night it is compiled, so it enters the graph already
        # attached instead of waiting to surface in a slice, which for a peripheral
        # note could take many sweeps and in practice often never came.
        #
        # One line per candidate anchor, ranked, capped per note. The cap is a reading
        # bound rather than a quality one: a note that matches nine anchors above the
        # floor is a note whose own subject is broad, and the cycle should attach it to
        # the few that say something rather than to every bucket it grazes.
        PER_NOTE = 5
        todays = {base(e["id"]) for e in notes if str(e.get("compiled", "")) == TODAY} & valid
        by_note = defaultdict(list)
        for t, hits in memb_props.items():
            for s, b in hits:
                if b in todays:
                    by_note[b].append((s, t))
        for b in sorted(by_note):
            for s, t in sorted(by_note[b], reverse=True)[:PER_NOTE]:
                what = "theme" if t in theme_slugs else (kind.get(t) or "note")
                print(f"ANCHOR\t{s}\t{b}\t{t}\t{len(members.get(t, ()))}\t{what}")
        sys.stderr.write(f"anchoring pass {TODAY}: {len(todays)} note(s) compiled this cycle, "
                         f"{sum(len(v[:PER_NOTE]) for v in by_note.values())} candidate anchor(s) "
                         f"for {len(by_note)} of them\n")
        return

    # Cluster detection (CONTRACT §7, rung 2 before rung 3). A note appearing in
    # three or more of the pairs a slice would draw is not n separate adjacencies;
    # it is a cluster, and a cluster wants one anchor decision rather than n pairwise
    # tags. n notes around a centre generate n(n-1)/2 pairwise candidates and need n
    # membership tags, which is the arithmetic behind two clusters (`deck-craft`, the
    # AI-prompt procedures) sitting in the lane for weeks as repeated pairwise noise
    # before a theme was minted by hand. Reported, never applied: minting an anchor is
    # a MINT decision with the person present, and the slice is what surfaces it.
    SLICE = 20
    CLUSTER_MIN = 3
    hot = Counter()
    for _adj, _c, _a, _b, _lane in prio_pairs[:SLICE]:
        hot[_a] += 1
        hot[_b] += 1
    clusters = [(n, k) for n, k in hot.most_common() if k >= CLUSTER_MIN]

    # An oversized anchor is reported only where this cycle is also proposing a tag
    # into it, so the question arrives with the decision it bears on rather than as
    # a standing complaint.
    growing = sorted({t for _s, _b, t in prio_memb if t in oversized},
                     key=lambda t: (-oversized[t][0], t))

    if PRIORITY_LIST:
        # One line per candidate, full precision, no PRIO_TOP truncation: pairs
        # first (score, cosine, a, b, lane), then memberships (score, note, anchor).
        # A caller wanting only pairs or only memberships filters on the first field.
        # Clusters lead the list, because rung 2 of the ladder is settled before
        # rung 3: a note carrying three or more of the slice's pairs is an anchor
        # question, and answering it removes those pairs rather than judging them.
        # An oversized anchor is the first question of all: it may absorb the very
        # memberships and pairs listed below it (CONTRACT §7, rung 2).
        lines = [f"OVERSIZED\t{oversized[t][0]}\t{oversized[t][1]}\t{t}" for t in growing]
        lines += [f"CLUSTER\t{k}\t{n}" for n, k in clusters]
        lines += [f"PAIR\t{adj}\t{c}\t{a}\t{b}\t{lane}" for adj, c, a, b, lane in prio_pairs]
        lines += [f"MEMB\t{s}\t{b}\t{t}" for s, b, t in prio_memb]
        # The lane is pinned for the day, and that is the whole point of the flag.
        # The coverage lane recomputes per note, so declining a candidate promotes
        # that note's next-ranked tie the moment the lane is re-derived, and a note
        # with a long weak tail hands the cycle one more candidate for every one it
        # rules out. That walk recurred five times between 2026-09-03 and 2026-09-07
        # and was stopped each time by a judgement call about diminishing return,
        # which is not a bound. Pinning makes it structural: the first call of the
        # day writes the lane, later calls return that same list, so a decline moves
        # its successor to the next cycle rather than into this one. `--refresh`
        # redraws deliberately; a new day redraws on its own.
        pinned = os.path.join(ROOT, "augment_wiki/priority-lane.json")
        prev = None
        if os.path.exists(pinned) and "--refresh" not in sys.argv[1:]:
            try:
                prev = json.load(open(pinned, encoding="utf-8"))
            except Exception:
                prev = None
        if prev and prev.get("drawn") == TODAY:
            sys.stderr.write(f"priority lane pinned {prev['drawn']}, "
                             f"{len(prev['lines'])} candidate(s); --refresh to redraw\n")
            lines = prev["lines"]
        else:
            with open(pinned, "w", encoding="utf-8") as f:
                json.dump({"drawn": TODAY, "lines": lines}, f, indent=1)
            sys.stderr.write(f"priority lane drawn {TODAY}, {len(lines)} candidate(s)\n")
        # Marked at display time, not baked into the pin: the lane's own candidates
        # do not change within a day, but verify-queue.md can (a sweep resolves a
        # batch mid-day), so a pair's pending status is re-read on every call rather
        # than frozen at the moment the lane was drawn.
        _, pending_pairs = read_queue_pending(ROOT, valid)
        if pending_pairs:
            marked = []
            for ln in lines:
                parts = ln.split("\t")
                if parts[0] == "PAIR":
                    pid = pending_pairs.get(frozenset((parts[3], parts[4])))
                elif parts[0] == "MEMB":
                    pid = pending_pairs.get(frozenset((parts[2], parts[3])))
                else:
                    pid = None
                marked.append(f"PENDING\t{pid}\t{ln}" if pid else ln)
            lines = marked
        for ln in lines:
            print(ln)
        return

    # Decay lane: the inverse of the convergent lane. A rebuilt note can stop
    # saying what its keyword edges were promoted for, and nothing else in the
    # system ever looks back at an edge once it is written, so a tag survives the
    # claim it recorded (the ERF case: a COMMENT scoped a framework down to an
    # unadopted competition proposal and the notes tagged to it kept pointing at
    # it). Scoped to notes recompiled today, because a source rewrite is what
    # makes an edge worth re-testing and a full sweep would re-propose the same
    # weak edges nightly. Cosine only, so this speaks to `Keywords` and never to a
    # sourced `## Links` entry, whose warrant is a source and whose re-reading is a
    # duty of the rebuild itself (DREAM phase 4).
    # Half the proposal floor: creating an edge and destroying one are not symmetric,
    # so removing a confirmed one needs the stronger evidence. Calibrated against the
    # live graph rather than picked: the weakest real edges on recompiled notes score
    # 0.045 to 0.061 and are all genuine cross-domain adjacencies the person confirmed
    # (MEPS to CSRD, Made to Stick to slidedoc), so a floor at 0.06 would propose
    # removing three good edges on its first night. Below 0.04 the two notes share
    # essentially no vocabulary.
    DECAY_FLOOR = 0.04
    recompiled = {base(e["id"]) for e in notes if e.get("compiled") == TODAY}
    decay, seen_decay = [], set()
    for b in sorted(recompiled & valid):
        for t in sorted(keywords_of(b)):
            pair = tuple(sorted((b, t)))
            if t not in valid or pair in kept or pair in seen_decay:
                continue
            seen_decay.add(pair)
            c = cos(b, t)
            if c < DECAY_FLOOR:
                decay.append((round(c, 3), pair[0], pair[1], b))
    decay.sort()

    # Filter-bubble lane (COGNITION §1, augmentation): the inverse of the
    # divergent lane. An anchor whose members converge (high internal similarity)
    # yet carries no `contradicts` edge anywhere in its cluster is a consensus the
    # wiki records only one side of: untested, not concluded. Surface it for a
    # DISCUSS pass; never gate. Ranked by internal convergence density.
    def density(mem):
        ps = list(combinations(sorted(mem), 2))
        if not ps:
            return 0.0
        return sum(cos(a, b) for a, b in ps) / len(ps)
    contra_notes = set()
    for a, b in contra_edges:
        contra_notes.add(a); contra_notes.add(b)
    bubbles = []
    for t, mem in members.items():
        if len(mem) < 3:                       # too small to call a consensus
            continue
        if (mem | {t}) & contra_notes:         # any recorded dissent -> not a bubble
            continue
        bubbles.append((round(density(mem), 3), t, len(mem)))
    bubbles.sort(reverse=True)

    # The standing backlog: proposals in the net that have never been judged. This is
    # not an inventory figure, it is what is owed. Every pair here is by construction
    # un-applied (a tag would have excluded it), un-linked, and un-dismissed, so the
    # net *is* the un-judged set and needs no separate "seen" ledger to be counted.
    # The three lanes are reported apart because they overlap slightly (a pair below
    # the convergent cut can reappear in coverage, and a membership proposal is a
    # note-to-anchor tie rather than a pair), so a single total would overstate its
    # own precision.
    memb_total = sum(len(v) for v in memb_props.values())
    backlog = len(cands) + len(coverage) + memb_total
    if STATUS:
        # The gate is not "is the net non-empty" (true by construction until fully
        # drained) but "is a presented batch sitting unanswered in the queue right
        # now". A CV-/MB-/SL- id only ever appears in verify-queue.md when a batch
        # was actually put to the person (VERIFY.md step 5); reading the net's size
        # as this signal is what stalled the pass for good the day this flag was
        # introduced (CHANGELOG 2026-08-26). Scoped to the curated tail, the
        # `## Queued for confirmation` marker onward, so a stable id quoted in the
        # generated header above it (there is none today, but nothing guarantees
        # that forever) can never be misread as a live batch.
        # Scoped to an id at the start of a numbered list line ("N. CV-...:"), the
        # one shape VERIFY step 5 actually presents a live item in. A resolved
        # batch's own summary paragraph names ids in prose (which pair was applied,
        # which was overridden) without ever losing them from the file, and a bare
        # \b-bounded match over the whole tail read those mentions as still-open
        # proposals: a batch fully resolved the same sweep it was drawn reported
        # itself outstanding, on 2026-08-27, caught only because the sweep that
        # wrote the resolution then ran --status itself and got a number that
        # could not be right against a page with no numbered list left on it.
        # An id appearing anywhere on a list line, numbered or bulleted. Both halves of
        # that tolerance are paid for. The list shape came first: a bulleted batch read
        # as absent and would have been drawn over (2026-08-29). The position came
        # second: VERIFY step 5's format moved the id to the end of the line, since a
        # person approves a change to their notes and should read that first, and a gate
        # anchored to the id's position went blind the moment the presentation improved
        # (2026-09-01, caught by --status reporting no batch outstanding against a live
        # 18-item list). A gate that constrains how a batch may be written will be broken
        # by the next thing that makes it readable, so it constrains only that the item
        # is a list line carrying an id. `read_queue_pending` is the one reading of this
        # file; `--priority-list` shares it to mark a pending pair rather than
        # re-presenting it as new (found 2026-09-12, see that function's docstring).
        outstanding, _pending_pairs = read_queue_pending(ROOT, valid)
        prio_note = (f"{priority_n} PRIORITY ({len(prio_pairs)} pairs, {len(prio_memb)} membership) "
                     f"touching a note compiled in the last {FRESH_DAYS} days"
                     if priority_n else "0 priority (nothing compiled recently)")
        if growing:
            head = ", ".join(f"{t} ({oversized[t][0]} members, density {oversized[t][1]})"
                             for t in growing[:3])
            more = f" and {len(growing) - 3} more" if len(growing) > 3 else ""
            prio_note += (f"; OVERSIZED first: {head}{more}, content notes carrying anchor duty and "
                          f"growing again this cycle, so ask what concept is missing before tagging in")
        if clusters:
            prio_note += ("; CLUSTER first: " +
                          ", ".join(f"{n} in {k}" for n, k in clusters) +
                          " of the 20 drawn pairs, an anchor question before a pairwise one")
        if outstanding and priority_n:
            # The pacing gate holds the backlog, never the priority lane: a candidate
            # belonging to freshly processed material is proposed at the next VERIFY
            # whatever else is open, since holding it until the backlog drains is the
            # delay this lane exists to remove. The backlog stays gated, so the total
            # cannot run away (DREAM phase 6).
            print(f"relations: {prio_note} OWED NOW, present them even though "
                  f"{len(outstanding)} id(s) are still unanswered; the backlog behind them stays "
                  f"gated ({backlog} standing: {len(cands)} convergent, {len(coverage)} coverage, "
                  f"{memb_total} membership)")
        elif outstanding:
            shown = ", ".join(outstanding[:8]) + (f", +{len(outstanding) - 8} more" if len(outstanding) > 8 else "")
            print(f"relations: batch OUTSTANDING, {len(outstanding)} id(s) still unanswered in "
                  f"verify-queue.md ({shown}); {prio_note}, so no fresh slice. "
                  f"{backlog} proposals remain standing in the net behind it "
                  f"({len(cands)} convergent, {len(coverage)} coverage, {memb_total} membership)")
        elif backlog:
            print(f"relations: pass OWED, no batch outstanding, {backlog} proposals standing and "
                  f"never presented ({len(cands)} convergent, {len(coverage)} coverage, "
                  f"{memb_total} membership); {prio_note} to draw first; "
                  f"{len(dismissed)} dismissed, {len(kept)} removals declined")
        else:
            print("relations: pass not owed, net empty "
                  "(every candidate applied or dismissed)")
        return

    out = fm_block(generated_by='augment/gen_relations.py', generated_at=STAMP, type='"[[hub]]"', status='"#current"') + ["# relations", "",
           "Adjacencies between wiki notes that no single source asserted, ranked "
           "by content similarity (TF-IDF over the note bodies) with co-citation and "
           "shared links as secondary boosters (CONTRACT §12). Deterministic and "
           "advisory: this view proposes, it never writes into a note. A pair is "
           "promoted into a `Keywords` tag at VERIFY (unsourced, §7), or escalated to "
           "a sourced `## Links` relationship where a source states the connection. "
           "Do not edit by hand.", "",
           f"**{backlog} proposals stand here, and none has been judged**: "
           f"{len(cands)} convergent, {len(coverage)} coverage, {memb_total} membership. "
           "Every pair in this view is un-tagged, un-linked and un-dismissed by "
           "construction, so what is listed is what is owed, not an inventory of what "
           "exists. A pass works a slice of it, never the whole, which is why the net "
           "standing still says nothing about its having been worked.", "",
           "## Priority (candidates touching a recently compiled note, for VERIFY)", "",
           f"**Draw these before the backlog** (DREAM phase 6): every candidate below touches a "
           f"note compiled within the last {FRESH_DAYS} days, so it belongs to material the person "
           "has just had processed and still holds the context for. They are not scored "
           "differently and they also appear in their home lane below; what this lane changes is "
           "the order they are read in, because a note compiled today otherwise enters a net of "
           "hundreds and waits out a backlog that takes many sweeps to drain. This lane is the one "
           "exception to the pacing gate: it is proposed at the next VERIFY even while an earlier "
           "batch stands unanswered, since deferring it is the delay the lane exists to remove.", ""]
    if growing:
        out.append("**Oversized anchors, first question of the slice.** A content note (not a theme) "
                   f"that {OVERSIZED_MIN} or more notes already keyword-tag, whose members hang "
                   f"together at density {OVERSIZED_DENSITY} or above, and that this cycle proposes to "
                   "grow again. That shape means a node is missing: the notes are gathering around "
                   "something nobody has written, or around a note doing double duty as a claim and as "
                   "a gathering point. Read the members and answer before tagging into it (CONTRACT §7).")
        out.append("")
        for t in growing:
            n, d = oversized[t]
            what = kind.get(t) or "note"
            out.append(f"- [[{t}]] ({what}, {n} members, internal density {d}). "
                       "Candidate: mint the missing concept, split the anchor, or leave it.")
        out.append("")
    if prio_pairs or prio_memb:
        out.append(f"**{priority_n} priority candidates** from {len(fresh_notes)} recently compiled "
                   f"note(s): {len(prio_pairs)} pairs, {len(prio_memb)} membership. "
                   f"Listing the strongest {min(priority_n, PRIO_TOP)}.")
        out.append("")
        shown_p = 0
        for adj, c, a, b, lane in prio_pairs[:PRIO_TOP]:
            out.append(f"- [[{a}]] and [[{b}]] (similarity {c}, {lane}). Candidate: keyword.")
            shown_p += 1
        for s, b, t in prio_memb[:max(0, PRIO_TOP - shown_p)]:
            out.append(f"- [[{b}]] into anchor [[{t}]] (similarity {s}). Candidate: keyword membership.")
            shown_p += 1
        if priority_n > shown_p:
            out.append(f"- (+{priority_n - shown_p} more priority candidates below the cut, "
                       "by descending score)")
    else:
        out.append(f"None. No note has been compiled in the last {FRESH_DAYS} days, so nothing "
                   "outranks the standing backlog this cycle.")
    out += ["",
           "## Convergent (candidate `Keywords` tags, for VERIFY)", ""]
    if cands:
        for adj, score, c, ss, neigh, sk, a, b in cands[:TOP]:
            bits = [f"similarity {c}"]
            if ss: bits.append(f"shared sources: {ss}")
            if neigh: bits.append(f"shared links: {neigh}")
            if sk: bits.append(f"same kind: {kind.get(a)}")
            out.append(f"- [[{a}]] and [[{b}]] ({', '.join(bits)}). Candidate: keyword.")
        if len(cands) > TOP:
            out.append(f"- (+{len(cands) - TOP} more below the cut, by descending score)")
    else:
        out.append("None above the similarity floor.")
    out += ["", "## Coverage (each note's strongest unlinked tie, for VERIFY)", "",
            "The wider echelon: for a note whose best tie never rose into the convergent "
            "top, its single strongest unlinked pair, so a peripheral note gets one candidate "
            "judged rather than staying invisible. Same VERIFY test as convergent, weighed the "
            "same way, but reached by breadth rather than rank. Work these alongside the "
            "convergent lane (roughly 60% coverage, 40% convergent, DREAM phase 6).", ""]
    if coverage:
        for adj, c, a, b in coverage:
            out.append(f"- [[{a}]] and [[{b}]] (similarity {c}). Candidate: keyword.")
    else:
        out.append("None above the coverage floor.")
    out += ["", "## Decay (existing `Keywords` edges that may no longer hold, for VERIFY)", "",
            "The inverse of the convergent lane: edges on notes **recompiled today** whose two "
            "notes now share almost no content. A source rewrite can take away what a tag was "
            "promoted for, and nothing else in the system looks back at an edge once written. "
            "Removal is a VERIFY decision like promotion, never the cycle's: a low cosine says "
            "the notes stopped overlapping, not that the person was wrong to connect them. "
            "Confirm with `apply_keywords.py --remove`; a declined removal is recorded "
            "`ruling: keep` and never re-proposed. Sourced `## Links` entries are not scored "
            "here, since their warrant is a source and re-reading it belongs to the rebuild "
            "(DREAM phase 4).", ""]
    if decay:
        for c, a, b, why in decay:
            out.append(f"- [[{a}]] and [[{b}]] (similarity {c}, below {DECAY_FLOOR}; "
                       f"[[{why}]] recompiled today). Candidate: remove keyword.")
    else:
        out.append("None. No edge on a note recompiled today fell below the decay floor.")
    out += ["", "## Divergent (existing `contradicts` edges, tension candidates)", ""]
    if contra_edges:
        for a, b in sorted(contra_edges):
            out.append(f"- [[{a}]] contradicts [[{b}]]. Tension candidate.")
    else:
        out.append("None.")
    out += ["", "## Membership (candidate `Keywords: [[anchor]]`, for VERIFY)", "",
            "Notes whose content matches an anchor's current members but that do not yet "
            "point at it. An anchor is any node two or more notes already keyword-tag: a "
            "theme, or a concept or entity acting as a gathering point. Confirm at VERIFY, "
            "so an anchor gathers its whole topic, not only what was tagged by hand.", ""]
    if memb_props:
        for t in sorted(memb_props):
            what = "theme" if t in theme_slugs else (kind.get(t) or "note")
            out.append(f"**[[{t}]]** ({what}, {len(members[t])} members):")
            for s, b in memb_props[t]:
                out.append(f"- [[{b}]] (similarity {s})")
            out.append("")
    else:
        out.append("None.")
    while out and out[-1] == "":
        out.pop()                              # trim any trailing blank before the next heading
    out += ["", "## Untested consensus (filter-bubble, for a DISCUSS pass)", "",
            "The inverse of the divergent lane (COGNITION §1, augmentation). Anchors whose "
            "members converge but that carry no `contradicts` edge anywhere in their cluster: "
            "a consensus the wiki records only one side of. A convergence with no dissent is a "
            "habit, not a conclusion. **Offer** a DISCUSS pass to steelman the counter-position; "
            "never gate, and \"just tell me\" ends it.", ""]
    if bubbles:
        for d, t, n in bubbles:
            what = "theme" if t in theme_slugs else (kind.get(t) or "note")
            out.append(f"- [[{t}]] ({what}, {n} members, internal convergence {d}), no recorded dissent.")
    else:
        out.append("None. Every convergence cluster carries a `contradicts` edge, or none is large enough to call.")
    out.append("")
    write_if_changed(os.path.join(ROOT, "augment_wiki/view/relations.md"), "\n".join(out))
    print(f"regenerated relations: {priority_n} priority candidates "
          f"({len(prio_pairs)} pairs, {len(prio_memb)} membership) from "
          f"{len(fresh_notes)} notes compiled in the last {FRESH_DAYS} days, "
          f"{len(cands)} convergent candidates "
          f"({min(len(cands), TOP)} shown), {len(coverage)} coverage candidates, "
          f"{len(contra_edges)} divergent edges, "
          f"{sum(len(v) for v in memb_props.values())} membership candidates, "
          f"{len(bubbles)} untested-consensus clusters, {len(decay)} decay candidates "
          f"from {len(recompiled & valid)} notes recompiled today, "
          f"{len(dismissed)} dismissed pairs excluded, {len(kept)} removals declined")

if __name__ == "__main__":
    main()
