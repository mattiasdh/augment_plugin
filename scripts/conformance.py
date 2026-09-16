#!/usr/bin/env python3
"""Conformance checks for the augment wiki (DREAM phase 5).

Deterministic and mechanical: run this, do not re-derive the checks each cycle
(re-deriving them is how the three link contexts got conflated into 15 false
dangling-link alarms). Exit 0 = clean, 1 = defects found, so it can gate an
automated cycle. Run from the vault root; the argument `.` is the vault root.

Checks, per DREAM phase 5:
  - index divergence: entry with no file, file with no entry, title/status mismatch
  - dangling links, separating the three contexts: a relationship target
    (`- <type> [[x]]`) must resolve to a wiki note; a `Source:` line, a
    `sources:` entry, a `## Decisions` line and a `further_sources:`
    anchor must resolve to a source file or the sources view
  - unsourced link context (a relationship with no Source line)
  - unsourced note (a concept/entity/tension citing no source; theme anchors are exempt, §3)
  - Keywords target not a content note (Tier-2 tag pointing at a hub or a missing note, §7)
  - invalid vocabulary (link type outside the three, status outside the set)
  - malformed note (title over ten words, no `sources:`, Type not matching folder)
  - provenance (CONTRACT §6): a wiki note with no `generated.by`, or one whose
    value is not the OKF `<producer>/<version>` actor form; a source whose
    `created:` postdates its `updated:`
  - fragile source filename (trailing space before .md, breaking wikilinks)
Advisories repeating past a handful are collapsed by kind with a count, so one
class firing on every note cannot bury the rest; findings are never collapsed.

  - sources: divergence (advisory): a note whose `sources:` field disagrees with the
    index's `compiled_from`, the mirror lagging the authoritative record (§4)
  - own working papers (advisory): a model-drafted source citing the practice's
    own notes as if they licensed a judgment (WRITE_FLOW §3)
  - counterfeit cleft (advisory): a cleft whose focus may be an anaphor rather
    than a new term, so it restates instead of contrasting (WRITE_FLOW §3)
  - metadiscourse (advisory): a model-drafted source whose body names the artefact
    ("ce dossier", "la présentation") instead of its subject, WRITE_FLOW §3
  - WRITE_FLOW section reference (advisory): a `WRITE_FLOW §N` pointing at a
    section that does not exist, the residue of a renumbering never re-pointed
  - queue integrity (advisory): a `CV-`/`MB-`/`SL-`/`RM-` id that `verify-queue.md`
    carried at HEAD and carries nowhere now, so an item was dropped by an edit
    rather than ruled on (VERIFY step 5)
  - run marker (advisory): `verify-queue.md` regenerated today with no `*_run` line
    in `history.jsonl` for today, so a cycle ran and left no trace in the ledger
    (CONTRACT §2)
Hubs and views (Type [[hub]]) and theme anchors are exempt from the source-citation checks.
Link extraction ignores fenced and inline `code` spans, so a note or dashboard that
documents link syntax in backticks is not misread as asserting the link; the
`further_sources:` anchor check runs on content notes only, never the dashboards.
"""
import datetime, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gen_util import split_note, links_in, load_config, scope_of

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
IDX = os.path.join(ROOT, "augment_wiki/index.jsonl")
LINK_TYPES = {"related", "example_of", "contradicts"}   # CONTRACT §7; was five until 2026-09-12
WIKI_STATUS = {"#current", "#stale", "#flagged", "#contested", "#superseded"}
TYPE_DIR = {"concept": "augment_wiki/concept", "entity": "augment_wiki/entity",
            "tension": "augment_wiki/tension", "theme": "augment_wiki/theme"}
CONTENT_TYPES = ("concept", "entity", "tension", "theme")
SOURCELESS_TYPES = ("theme",)   # anchors that cite no source, like hubs (CONTRACT §3)

_FENCE = re.compile(r"```.*?```", re.S)
_INLINE = re.compile(r"`[^`]*`")

RANGE_EN = re.compile(r'\d\s*\u2013\s*\d')
_WIKILINK = re.compile(r"\[\[[^\]]*\]\]")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
STAMP_RE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:[ T]\d{2}:\d{2})?")

# Artefact self-reference, the greppable half of WRITE_FLOW §3's subject-or-document
# test. Determiner plus noun in the three languages the archive writes in, so a bare
# "dossier" or "nota" (which usually names the client's case, not this file) does not
# fire. Kept narrow deliberately: a missed instance costs a reading pass, a noisy
# check gets ignored.
SELF_REF = re.compile(
    r"\b(?:"
    r"ce (?:dossier|document|chapitre)|cette (?:note|présentation|section|page)|"
    r"la présentation|le présent document|"
    r"dit (?:document|dossier|hoofdstuk)|deze (?:nota|presentatie|sectie)|"
    r"this (?:document|note|section|chapter|presentation)"
    r")\b", re.I)
# The practice's own working papers cited as if they were an authority
# (WRITE_FLOW §3). One step out from SELF_REF: naming the archive rather than
# the document. In a deliverable the practice authors, its notes are where a
# judgment was recorded, not a source that licenses it, and in the bilingual
# pair that prompted this the Dutch form also hid which party had spoken.
OWN_PAPERS = re.compile(
    r"\b(?:"
    r"(?:nos|notre)\s+(?:propres\s+)?(?:notes|carnets|relev[ée]s)|"
    r"(?:de|onze)\s+eigen\s+(?:nota'?s?|notities|aantekeningen)|"
    r"(?:our|the practice's)\s+own\s+(?:notes|records)"
    r")\b", re.I)

# Counterfeit cleft (WRITE_FLOW §3): a cleft whose focused element is a
# demonstrative pointing back at what was just said, so it introduces no term
# and only asserts that the previous sentence mattered. The test is the focus,
# not the construction: a cleft focusing a *new noun* carries a real contrast
# and is deliberately not matched here. Advisory, because the anaphor/new-term
# distinction is finally a reading judgement in every language.
CLEFT = re.compile(
    r"(?:"
    r"c'est\s+(?:ce|cet|cette|ces|cela|ça)\b[^.;:]{0,40}?\bqu[ie]\b|"
    r"\b(?:est|sont)\s+ce\s+qu[ie]\b|"
    r"\b(?:precies|juist)\s+(?:dat|dit|die|deze)\b[^.;:]{0,40}?\b(?:is|zijn)\s+wat\b|"
    # English clefts always focus an anaphor ("that is what…"), so the focus test
    # alone cannot separate them; a second anaphor after the wh-word is what marks
    # a genuine restatement. "and that is what makes a column scannable" adds a
    # mechanism and clears; "and that is what this shows" adds nothing and fires.
    r"\b(?:and\s+)?(?:that|this)\s+is\s+(?:exactly\s+)?(?:what|why)\s+(?:this|that|it)\b|"
    r"\bwhich\s+is\s+(?:exactly\s+)?what\s+(?:this|that|it)\b"
    r")", re.I)

ACTOR_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")   # OKF `<producer>/<version>` (§6)


def strip_code(txt):
    """Blank out fenced blocks and inline `code` spans so documented link syntax
    is not read as a live link. A note (or a dashboard) that writes `[[x]]` inside
    backticks is describing the syntax, not asserting the link."""
    return _INLINE.sub(" ", _FENCE.sub(" ", txt))

def rel(p):
    return os.path.relpath(p, ROOT)


def note_stamp(fm):
    """The content-change stamp of a note, whichever layer it belongs to.

    Wiki notes carry it as `generated.at` since the OKF alignment (CONTRACT §4);
    source notes keep a flat `updated:`, because the source layer is the person's
    and is not rewritten to a convention that serves the derived one (§5). One
    reader here rather than the same two-branch lookup at each call site.
    """
    g = fm.get("generated")
    if isinstance(g, dict) and g.get("at") is not None:
        return str(g["at"]).strip().strip('"')
    return str(fm.get("updated", "")).strip().strip('"')


def actor_of(fm):
    """The `generated.by` value, or "" when absent."""
    g = fm.get("generated")
    return str(g.get("by", "")).strip().strip('"') if isinstance(g, dict) else ""

def source_files(config):
    """Every path that could be a source. What is *not* one comes from the vault's
    own `scope.ignore` (CONTRACT §9) rather than a list baked in here, since which
    folders are scratch and which are knowledge is a property of the vault, not of
    the system. `augment_wiki/`, `augment_plugin/` and dotfolders are structural and
    stay hard-coded: the wiki is derived, the plugin is method, and neither is ever
    a source whatever the config says."""
    out = []
    for p in glob.glob(os.path.join(ROOT, "**/*.md"), recursive=True):
        r = rel(p)
        if r.split("/")[0] in ("augment_wiki", "augment_plugin") or r.startswith("."):
            continue
        if scope_of(r, config) == "ignore":
            continue
        out.append(r)
    return out

def main():
    idx = [json.loads(l) for l in open(IDX, encoding="utf-8") if l.strip()]
    cfg = load_config(ROOT)
    byid = {e["id"]: e for e in idx}
    findings = []       # defects: fail the run (wiki-layer integrity)
    advisories = []     # surface to VERIFY, do not fail (source-layer hygiene)

    wiki_files = [rel(p) for p in glob.glob(os.path.join(ROOT, "augment_wiki/**/*.md"), recursive=True)]
    wiki_base = {os.path.splitext(os.path.basename(p))[0] for p in wiki_files}
    srcs = source_files(cfg)
    src_base = {os.path.splitext(os.path.basename(p))[0] for p in srcs}

    # future metadata dates (defect: a bookkeeping date ahead of today was typed
    # from inference, not read from the clock, which is how a session bumped the
    # ISO date like a version number across successive edits). Only *metadata*
    # dates are checked: prose legitimately cites future years (a 2030 deadline),
    # so the body is never scanned.
    today = datetime.date.today().isoformat()
    for e in idx:
        for field in ("compiled", "processed", "declared", "ran", "deleted"):
            v = e.get(field)
            if isinstance(v, str) and DATE_RE.fullmatch(v) and v > today:
                findings.append(f"future {field} date {v} (today {today}): {e['id']}")
    for p_ in wiki_files:
        fm_, _ = split_note(open(os.path.join(ROOT, p_), encoding="utf-8").read())
        u = note_stamp(fm_)
        m = STAMP_RE.fullmatch(u)
        if m and m.group(1) > today:
            findings.append(f"future generated.at {u} (today {today}): {p_}")
    # stale updated: (advisory). The future-date check catches a date typed ahead
    # of the work; this catches the commoner slip, a date read once at the start of
    # a session and carried across a day boundary, so a note edited today still
    # claims yesterday. Scoped to files git records as changed *today*, because a
    # status-only or keyword edit legitimately leaves updated: alone (CONTRACT §9)
    # and older touches cannot be told apart from those without a per-note content
    # hash, which the index does not keep. Advisory for that reason: it names a
    # likely slip, it does not gate the build.
    try:
        import subprocess
        out = subprocess.run(["git", "log", "--since=midnight", "--format=", "--name-only"],
                             cwd=ROOT, capture_output=True, text=True, timeout=30).stdout
        touched_today = {ln.strip() for ln in out.splitlines() if ln.strip()}
    except Exception:
        touched_today = set()
    for p_ in sorted(set(wiki_files) | set(srcs)):     # source notes carry it too
        if p_.startswith(("augment_wiki/hub/", "augment_wiki/view/")):
            continue                          # generated wholesale; write_if_changed already
                                               # holds the stamp to real content changes, so a
                                               # rename or unrelated same-day commit touching the
                                               # file is not the human slip this check looks for
        if p_ not in touched_today:
            continue
        try:
            fm_, _ = split_note(open(os.path.join(ROOT, p_), encoding="utf-8").read())
        except Exception:
            continue
        u = note_stamp(fm_)
        m = STAMP_RE.fullmatch(u)
        if m and m.group(1) < today:
            label = "generated.at" if p_.startswith("augment_wiki/") else "updated:"
            advisories.append(f"{label} {u} but content changed today ({today}): {p_}")

    # source-layer stamps (§4): `created:` is written once when the note is first made
    # and `updated:` on every edit, so the first can never postdate the second. Catches a
    # created: typed from inference rather than read from the clock (§6).
    for p_ in srcs:
        try:
            fm_, _ = split_note(open(os.path.join(ROOT, p_), encoding="utf-8").read())
        except Exception:
            continue
        c = str(fm_.get("created", "")).strip().strip('"')
        u = str(fm_.get("updated", "")).strip().strip('"')
        if c and u and STAMP_RE.fullmatch(c) and STAMP_RE.fullmatch(u) and c > u:
            findings.append(f"created: {c} postdates updated: {u}: {p_}")

    # WRITE_FLOW section references resolve. The file was recast into three passes
    # on 2026-08-11 and renumbered; nothing was re-pointed, so every live reference
    # to it in the repo went stale at once and four of them were printed to the user
    # by the typography findings below, sending them to a section that did not exist.
    # Advisory: a dangling § misdirects a reader, it does not corrupt the wiki. The
    # rules file now ships with the plugin, so it is read from the plugin root and
    # the vault is what gets scanned for references into it.
    hs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "..", "rules", "write-flow.md")
    if os.path.exists(hs_path):
        hs_sections = set(re.findall(r"(?m)^##\s+(\d+)\.",
                                     open(hs_path, encoding="utf-8").read()))
        ref_re = re.compile(r"WRITE[_ ]FLOW(?:\.md)?\s+§(\d+)")
        scan = [p for p in glob.glob(os.path.join(ROOT, "**/*.md"), recursive=True)
                + glob.glob(os.path.join(ROOT, "**/*.py"), recursive=True)
                if not rel(p).startswith("notes/_inbox/")
                and not rel(p).split("/")[0].startswith(".")]
        for p in sorted(scan):
            try:
                txt = open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            for n in sorted(set(ref_re.findall(txt))):
                if n not in hs_sections:
                    advisories.append(
                        f"WRITE_FLOW §{n} referenced but no such section: {rel(p)}")

    # queue integrity: an item id that was in `verify-queue.md` at HEAD and is in no
    # part of the working copy has been dropped, not answered. A sweep edits the
    # queue's curated tail by replacing a span of prose, and a span replacement
    # cannot tell an item it meant to resolve from one that merely sat next to it:
    # on 2026-09-03 four unresolved items went out with the edit and a freed id was
    # then reissued to a different pair. Nothing else checks this, because every
    # other check reads the file that remains rather than the one it replaced.
    # Deterministic and one-sided: it compares two texts and only ever reports
    # disappearance. An id may legitimately leave, once its ruling is in the
    # history, so this is an advisory the sweep answers rather than a defect.
    try:
        import subprocess
        was = subprocess.run(["git", "show", "HEAD:augment_wiki/verify-queue.md"],
                             cwd=ROOT, capture_output=True, text=True, timeout=30)
        if was.returncode == 0:
            qp = os.path.join(ROOT, "augment_wiki/verify-queue.md")
            now = open(qp, encoding="utf-8").read() if os.path.exists(qp) else ""
            id_re = re.compile(r"\b(?:CV|MB|SL|RM)-\d{4}-\d{2}-\d{2}-\d+\b")
            gone = sorted(set(id_re.findall(was.stdout)) - set(id_re.findall(now)))
            if gone:
                advisories.append(
                    "verify-queue.md no longer mentions " + ", ".join(gone) +
                    " (present at HEAD): confirm each was ruled on, not dropped")
    except Exception:
        pass

    # run marker: a cycle that regenerated the queue today left no `*_run` line in
    # history for today. CONTRACT §2 asks for one marker per cycle, and it is the
    # only place the ledger records that a cycle happened at all; a note entry says
    # a note was written, not that a run produced it. The marker is appended by hand
    # as one late write among several in phases 7 and 8, and nothing checked it, so
    # it went missing twice in one week (INCIDENTS, 2026-09-09) and both gaps were
    # found by someone reading the ledger for an unrelated reason. The proxy is the
    # queue's own "Last regenerated" stamp, which only a real cycle writes: if that
    # says today, a run happened today and owes a marker. Advisory rather than a
    # defect, because a session may legitimately regenerate the header outside a
    # cycle (a VERIFY refreshing its counts, as this one does), and because the
    # honest repair is to append the marker rather than to reconstruct a timestamp
    # nobody read (CONTRACT §6 bars a typed `created:` for the same reason).
    #
    # It catches the first of the two 2026-08 instances and not the second. A day
    # with no marker at all is visible here; a *second* cycle on a day that already
    # has one is not, because nothing records how many cycles ran, only that one
    # did. Covering that would mean counting cycles, and the §2 `-2` suffix is a
    # naming convention rather than a count. Said plainly rather than left implied,
    # since a check believed to cover more than it does is worse than none.
    try:
        qp = os.path.join(ROOT, "augment_wiki/verify-queue.md")
        stamp_re = re.compile(r"(?m)^Last regenerated:\s*(\d{4}-\d{2}-\d{2})")
        m = stamp_re.search(open(qp, encoding="utf-8").read()) if os.path.exists(qp) else None
        if m and m.group(1) == today:
            hp = os.path.join(ROOT, "augment_wiki/history.jsonl")
            marked = False
            for line in open(hp, encoding="utf-8"):
                line = line.strip()
                if not line or "_run" not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if not str(rec.get("kind", "")).endswith("_run"):
                    continue
                # `ran` is where a run marker carries its timestamp; the id is the
                # fallback, since it is `<kind>-<date>` by construction (§2) and a
                # same-day rerun suffixes it rather than changing its shape.
                if today in str(rec.get("ran", "")) or today in str(rec.get("id", "")):
                    marked = True
                    break
            if not marked:
                advisories.append(
                    f"verify-queue.md was regenerated {today} but history.jsonl carries no "
                    f"*_run marker for {today} (CONTRACT §2): append the cycle's marker, or "
                    f"disregard if this was a header refresh outside a cycle")
    except Exception:
        pass

    # autonomy audit (advisories). DREAM applies its own convergence and anchoring
    # verdicts without confirmation (CONTRACT §12), which moves the person's work from
    # approving each write to auditing the batch. That audit needs a surface, and these
    # three are it: what was written unattended, where the writing ran hot, and what the
    # cycle flagged and then left. Advisory by construction: every one of them can be
    # the correct state, and the sweep answers them rather than the run failing on them.
    try:
        hp = os.path.join(ROOT, "augment_wiki/history.jsonl")
        auto_since, runs, tag_growth = 0, set(), {}
        last_verify_id = ""
        recs = []
        for line in open(hp, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except ValueError:
                continue
        # Position, not date. history.jsonl is append-only and strictly ordered, so
        # "since the last sweep" means "after the last verify_run marker in file
        # order", never a date comparison: a same-day DREAM run after a same-day
        # VERIFY carries the same YYYY-MM-DD as the marker it followed, and every
        # date-truncated comparison silently dropped it (found 2026-09-14, fixed
        # 2026-09-16). Position survives same-day recurrence by construction.
        last_verify_idx = -1
        for i, rec in enumerate(recs):
            if str(rec.get("kind", "")) == "verify_run":
                last_verify_idx = i
                last_verify_id = str(rec.get("id", ""))
        for i, rec in enumerate(recs):
            if not rec.get("auto") or i <= last_verify_idx:
                continue
            auto_since += 1
            runs.add(str(rec.get("run", "")))
            tag_growth[rec.get("id")] = tag_growth.get(rec.get("id"), 0) + \
                len(re.findall(r"Keyword \[\[[^\]]+\]\] gained", str(rec.get("note", ""))))
        if auto_since:
            advisories.append(
                f"{auto_since} autonomous write(s) across {len(runs)} run(s) since the last "
                f"recorded sweep{' (' + last_verify_id + ')' if last_verify_id else ''}: audit "
                f"them, `undo_run.py . <run-id>` reverts a night")
        # Runaway attaching: one note gaining many tags unattended is what an
        # over-eager anchoring pass looks like from the outside, and it is the failure
        # this automation could produce that no other check would see. The floor is a
        # reading bound, not a claim about the right number of tags: a note that
        # genuinely belongs to six anchors is fine, and saying so at the sweep costs
        # one line.
        RUNAWAY = 6
        hot = sorted((n, c) for n, c in tag_growth.items() if c >= RUNAWAY)
        for n, c in hot:
            advisories.append(
                f"{c} keyword(s) attached unattended since the last sweep, check the note is "
                f"not over-anchored: {n}")
    except Exception:
        pass

    # typography, WRITE_FLOW §2 (defect on wiki notes: the layer is model-written,
    # so a barred mark is the model's own slip and nothing downstream will catch it).
    # An unpaired en dash between clauses is the em dash under another glyph; a paired
    # one is allowed, so parity per line is the cheap, deterministic proxy.
    for p_ in wiki_files:
        txt_ = open(os.path.join(ROOT, p_), encoding="utf-8").read()
        # Link targets are quoted identifiers owned by the person (a source filename
        # may carry any mark, and a citation must reproduce it or the link breaks),
        # so they are blanked before the prose is judged. WRITE_FLOW §0.
        body_ = _WIKILINK.sub(" ", strip_code(txt_))
        if "\u2014" in body_:
            findings.append(f"em dash (WRITE_FLOW §2): {p_}")
        if "\u00b7" in body_:
            findings.append(f"middle dot (WRITE_FLOW §2): {p_}")
        for ln in body_.splitlines():
            if ln.lstrip().startswith("|"):
                continue                      # table rows carry their own dashes
            if ln.count("\u2013") % 2 and not RANGE_EN.search(ln):
                findings.append(f"unpaired en dash (WRITE_FLOW §2): {p_}")
                break

    # metadiscourse: prose naming the artefact instead of its subject (WRITE_FLOW §3).
    # Scoped to model-drafted sources, which declare `assisted_by:`; the person's own
    # notes are never judged (§0, the test is authorship). The `> [!ai]` callout is
    # excluded because writing *about* the text is exactly what belongs there, and
    # headings are excluded because a section may legitimately be named for the
    # document's own structure. Advisory, not a defect, and honestly so: "le dossier"
    # can name the client's case file rather than this file, and only a reader tells
    # which. This catches the artefact-naming half of the check; the positional half
    # (first and last sentence of every section) stays a reading job.
    for p_ in sorted(srcs):
        try:
            txt_ = open(os.path.join(ROOT, p_), encoding="utf-8").read()
        except Exception:
            continue
        if "assisted_by:" not in txt_:
            continue
        _, body_ = split_note(txt_)
        hits, papers, clefts = set(), set(), set()
        for ln in strip_code(body_).splitlines():
            s = ln.strip()
            if not s or s.startswith((">", "#", "|", "[^")):
                continue          # callout, heading, table row, footnote definition
            for m in SELF_REF.finditer(s):
                hits.add(m.group(0).lower())
            for m in OWN_PAPERS.finditer(s):
                papers.add(m.group(0).lower())
            for m in CLEFT.finditer(s):
                clefts.add(m.group(0).lower())
        if hits:
            advisories.append(
                f"names the document rather than its subject "
                f"({', '.join(sorted(hits))}), WRITE_FLOW §3: {p_}")
        if papers:
            advisories.append(
                f"cites the practice's own working papers as an authority "
                f"({', '.join(sorted(papers))}), WRITE_FLOW §3: {p_}")
        if clefts:
            advisories.append(
                f"counterfeit cleft, check the focus is a new term and not an "
                f"anaphor ({', '.join(sorted(clefts))}), WRITE_FLOW §3: {p_}")

    # index/source status divergence: a source the index calls #processed must carry
    # the matching `augment:` declaration. The two writes are separate, so a harvest
    # transaction can complete the index entry and silently skip the source tag,
    # which is exactly what happened to 31 files in one project-log batch and
    # was caught only by chance the following cycle. Advisory, not a defect: the
    # index is authoritative for what was processed, and the inline tag is the
    # person-facing mirror of it (CONTRACT §5), so a gap is a sync to make, not a
    # broken wiki. A retired path (deleted or renamed) has no file to carry a tag.
    for e in idx:
        i = str(e.get("id", ""))
        if i.startswith("augment_wiki/") or e.get("status") != "processed":
            continue
        f = os.path.join(ROOT, i)
        if not os.path.exists(f):
            continue
        head = open(f, encoding="utf-8", errors="replace").read()
        fm_, _ = split_note(head)
        if "#processed" not in str(fm_.get("augment", "")):
            advisories.append(f"index says #processed, source's augment: does not: {i}")

    # fragile source filenames (advisory: renaming a source is a human/VERIFY act)
    for p in srcs:
        if p[:-3].endswith(" ") or "  " in os.path.basename(p):
            advisories.append(f"fragile filename (trailing/double space): {p}")

    # index divergence: entries vs files
    note_entries = [e for e in idx if str(e["id"]).startswith("augment_wiki/")
                    and e.get("type") in CONTENT_TYPES]
    content_base = {os.path.splitext(os.path.basename(e["id"]))[0] for e in note_entries}
    for e in note_entries:
        if not os.path.exists(os.path.join(ROOT, e["id"])):
            findings.append(f"index entry with no file: {e['id']}")
    entry_ids = {e["id"] for e in note_entries}
    for p in wiki_files:
        d = p.split("/")
        if len(d) == 3 and d[1] in CONTENT_TYPES and p not in entry_ids:
            findings.append(f"note file with no index entry: {p}")

    # per-note conformance
    for e in note_entries:
        path = e["id"]
        full = os.path.join(ROOT, path)
        if not os.path.exists(full):
            continue
        txt = open(full, encoding="utf-8").read()
        fm, _ = split_note(txt)         # metadata is frontmatter (CONTRACT §4)
        body = strip_code(txt)          # link extraction ignores code-span-quoted syntax
        lines = txt.splitlines()
        typ = e["type"]
        title = next((l[2:].strip() for l in lines if l.startswith("# ")), "")
        status = str(fm.get("status", "")).strip()

        if e.get("title") != title:
            findings.append(f"index/title divergence: {path}")
        if e.get("status") != status:
            findings.append(f"index/status divergence: {path}")
        if status not in WIKI_STATUS:
            findings.append(f"invalid status {status!r}: {path}")
        if len(title.split()) > 10:
            findings.append(f"title over ten words: {path}")
        if TYPE_DIR.get(typ) and not path.startswith(TYPE_DIR[typ] + "/"):
            findings.append(f"Type {typ} not in {TYPE_DIR[typ]}/: {path}")

        sourceless = typ in SOURCELESS_TYPES     # theme anchors cite no source (§3)
        cited = links_in(fm.get("sources"))
        if not cited and not sourceless:
            findings.append(f"no sources: (cites nothing): {path}")

        # provenance (§6): the whole wiki layer is written by something, and since the
        # OKF alignment each note says by what. Absent or free-text is a defect, since
        # the value's whole use is being groupable and greppable across the archive.
        by = actor_of(fm)
        if not by:
            findings.append(f"no generated.by: {path}")
        elif not ACTOR_RE.fullmatch(by):
            findings.append(f"generated.by not <producer>/<version> ({by!r}): {path}")

        # Keywords header (Tier 2, §7): bare wikilinks to CONTENT notes only, never hubs
        for t in links_in(fm.get("keywords")):
            if t not in content_base:
                findings.append(f"Keywords target not a content note [[{t}]]: {path}")

        # relationship links + their Source lines (## Links block)
        if "## Links" in body:
            # Bounded by the next `## ` heading, not by `## Sources`, which moved into
            # frontmatter: splitting on it would swallow `## Decisions` and `## Notes`.
            block = re.split(r"\n## ", body.split("## Links", 1)[1], maxsplit=1)[0]
            entries = re.split(r"\n(?=- )", block)
            for ent in entries:
                m = re.match(r"- (\w+) \[\[([^\]|]+)\]\]", ent.strip())
                if not m:
                    continue
                lt, tgt = m.group(1), m.group(2)
                if lt not in LINK_TYPES:
                    findings.append(f"invalid link type {lt!r}: {path}")
                if tgt not in wiki_base:
                    findings.append(f"dangling relationship link [[{tgt}]]: {path}")
                if "Source:" not in ent:
                    findings.append(f"unsourced link context ({lt} [[{tgt}]]): {path}")

        # Source: citations + sources: entries -> source files
        for s in re.findall(r"^\s*Source: \[\[([^\]|]+)\]\]", body, flags=re.M):
            if s not in src_base:
                findings.append(f"Source citation not a source file [[{s}]]: {path}")
        for s in cited:
            if s not in src_base:
                findings.append(f"sources: entry not a source file [[{s}]]: {path}")

        # ## Decisions lines -> source files
        if "## Decisions" in body:
            for s in re.findall(r"\[\[([^\]|#]+)\]\]", body.split("## Decisions", 1)[1]):
                if s not in src_base:
                    findings.append(f"decision citation not a source file [[{s}]]: {path}")

    # `sources:` against the index's `compiled_from` (advisory). The index is
    # authoritative for build provenance and the note's `sources:` field is its
    # person-facing mirror (§4), so the two saying different things means the mirror
    # lagged: the commonest cause is a source renamed with the citing notes not
    # repointed. Advisory rather than defect for the same reason as the inline-Status
    # guard: the index is authoritative, so the build is not wrong, only the page.
    for e in note_entries:
        if e.get("type") not in ("concept", "entity", "tension"):
            continue
        f = os.path.join(ROOT, e["id"])
        if not os.path.exists(f):
            continue
        fm_, _ = split_note(open(f, encoding="utf-8").read())
        # A wikilink target carries no extension, so it is compared as written: running
        # splitext over it truncates any target containing a dot (a citation like
        # "Author. Title, Subtitle" loses everything after the first dot), which
        # produced a false divergence on nine notes.
        shown = set(links_in(fm_.get("sources")))
        built = {os.path.basename(c["source"] if isinstance(c, dict) else c)[:-3]
                 for c in e.get("compiled_from", [])}
        if shown != built:
            miss = sorted(built - shown) or sorted(shown - built)
            advisories.append(f"sources: diverges from the index compiled_from ({miss}): {e['id']}")

    # `further_sources:` anchors -> a heading in the sources view. The whole file text is
    # scanned, so the anchor is found in frontmatter where it now lives. Checked on content
    # notes only (the sole place it appears); the hub/view dashboards are exempt,
    # as they are from the source-citation checks, since they document link syntax in prose.
    sv = os.path.join(ROOT, "augment_wiki/view/sources.md")
    heads = set()
    if os.path.exists(sv):
        heads = set(re.findall(r"^## (.+)$", open(sv, encoding="utf-8").read(), flags=re.M))
    for e in note_entries:
        full = os.path.join(ROOT, e["id"])
        if not os.path.exists(full):
            continue
        for a in re.findall(r"\[\[sources#([^\]]+)\]\]", strip_code(open(full, encoding="utf-8").read())):
            if a not in heads:
                findings.append(f"unresolved sources# anchor [[sources#{a}]]: {e['id']}")

    # publish leak: client identity inside a file the export manifest ships.
    # The system layer is written to be forked, and its rules are argued from worked
    # examples, which in this archive means real clients and real jobs. Export-time
    # scrubbing is not enough on its own: the leak arrives months later, when a cycle
    # writes a fresh failing-case example naming a current project into an operation
    # file, and the next export carries it out. So the guard runs here, every cycle,
    # against a denylist derived from the vault's own entity and scope entries
    # (_publish.py) and never written down anywhere publishable.
    from _publish import leak_terms, published_files
    terms = leak_terms(idx, cfg)
    for p_ in published_files(ROOT):
        try:
            txt_ = open(os.path.join(ROOT, p_), encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        hit = sorted({t for t in terms
                      if re.search(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])",
                                   txt_, flags=re.I)})
        if hit:
            findings.append(f"publish leak, client identity in a published file {hit}: {p_}")

    # release drift (advisory). The method ships separately from the content it
    # compiles, so the two can drift silently: a vault compiled under one release
    # and read under another is exactly the case where a rule changed underneath
    # the wiki with nothing in the output to show it. Advisory rather than a
    # defect, because adopting a release is the person's decision and a vault is
    # legitimately one release behind between the install and the sweep.
    declared = str(cfg.get("plugin_version", "")).strip()
    try:
        manifest = json.load(open(os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", ".claude-plugin", "plugin.json"), encoding="utf-8"))
        installed = str(manifest.get("metadata", {}).get("release", "")).strip()
    except Exception:
        installed = ""
    if declared and installed and declared != installed:
        advisories.append(
            f"release drift: config.yaml declares {declared}, the installed plugin "
            f"is {installed}; adopt it or pin the plugin")
    elif not declared:
        advisories.append(
            "config.yaml declares no plugin_version, so a release change cannot be detected")

    if advisories:
        # Collapsed by kind past a threshold. An advisory class that fires on a
        # hundred files is reporting one thing, not a hundred, and printing it a
        # hundred times buries every other class in the run: a schema migration
        # touches every note in a day and sets the stale-stamp check off on all of
        # them. Findings are never collapsed, since each one has to be answered.
        SHOW = 5
        def kind(a):
            """The advisory's class: its message with the file and every date removed."""
            return re.sub(r"\d", "#", a.rsplit(": ", 1)[0])
        groups = {}
        for a in advisories:
            groups.setdefault(kind(a), []).append(a)
        print(f"ADVISORIES (surface to VERIFY, non-blocking): {len(advisories)}")
        for k, g in groups.items():
            for a in g[:SHOW]:
                print("  ~", a)
            if len(g) > SHOW:
                print(f"  ~ (+{len(g) - SHOW} more: {k})")
    if findings:
        print(f"CONFORMANCE DEFECTS: {len(findings)}")
        for f in findings:
            print("  -", f)
        sys.exit(1)
    print(f"CONFORMANCE: clean ({len(note_entries)} notes checked)")

if __name__ == "__main__":
    main()
