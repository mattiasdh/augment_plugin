#!/usr/bin/env python3
"""Regenerate the derivable header of augment_wiki/verify-queue.md (DREAM phase 8).

The queue is a CURRENT-STATE dashboard, not an append log. Everything above the
`## Queued for confirmation` marker (State, Health, Undeclared census) is
regenerated from index.jsonl on every run, so those numbers are never stale.
Everything from the marker down is CURATED: the live judgement items DREAM
reconciles each run (dropping what VERIFY resolved), plus the previous run's
log. That curated tail is preserved untouched. Run from the vault root.
"""
import glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gen_util import stamp, load_config, scope_of, undecided_folders, display_path
from collections import Counter

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
IDX = os.path.join(ROOT, "augment_wiki/index.jsonl")
QUEUE = os.path.join(ROOT, "augment_wiki/verify-queue.md")
MARK = "## Queued for confirmation"
STAMP = stamp()

def main():
    idx = [json.loads(l) for l in open(IDX, encoding="utf-8") if l.strip()]
    cfg = load_config(ROOT)
    scope = cfg.get("scope") or {"rules": []}
    harvest = cfg.get("harvest") or {}
    notes = [e for e in idx if str(e["id"]).startswith("augment_wiki/") and e.get("type") in ("concept", "entity", "tension", "theme")]
    # Source ids are repo-relative paths and end in `.md` (CONTRACT §9); excluding the
    # bookkeeping entries by name instead counted `config` and `restyle` as sources.
    srcs = [e for e in idx if str(e["id"]).endswith(".md") and not str(e["id"]).startswith("augment_wiki/")]
    typ = Counter(e.get("type") for e in notes)
    st = Counter(e.get("status") for e in notes)
    unlinked = [e for e in srcs if not e.get("produced")]

    # Harvest progress (generated): files processed of total per decision-harvest folder,
    # so the backlog is computed from the index and disk, never hand-written prose that drifts.
    processed_ids = {e["id"] for e in srcs if e.get("status") == "processed"}
    hdirs = {}      # reldir -> label
    for p in harvest.get("paths", []):
        m = re.match(r"(.+?)\s*>=\s*(\d+)", p)     # a rule like "10_PROJECTS >=200 project logs"
        if m:
            base, thr = m.group(1).strip(), int(m.group(2))
            bd = os.path.join(ROOT, base)
            if os.path.isdir(bd):
                for name in sorted(os.listdir(bd)):
                    lead = re.match(r"(\d+)", name)
                    if os.path.isdir(os.path.join(bd, name)) and lead and int(lead.group(1)) >= thr:
                        hdirs[os.path.join(base, name)] = name
        elif os.path.isdir(os.path.join(ROOT, p)):  # a literal project folder
            hdirs[p] = os.path.basename(p)
    hrows, htot_done, htot_all = [], 0, 0
    for d, label in hdirs.items():
        files = [os.path.relpath(f, ROOT) for f in glob.glob(os.path.join(ROOT, d, "**/*.md"), recursive=True)]
        done = sum(1 for f in files if f in processed_ids)
        htot_done += done
        htot_all += len(files)
        hrows.append((len(files) - done, done, len(files), label))
    hrows.sort(key=lambda r: (-r[0], r[3]))

    # Declared-folder backlog visibility (generated): an in-scope `#to-process`
    # folder can sit with files never touched by any pass and nothing here would
    # say so. detect_changes.py only compares hashes already in index.jsonl, and
    # the Harvest section above only walks harvest.paths, so neither one walks the
    # general #to-process scope against the filesystem. Found the hard way when two
    # newly-declared folders sat fully unindexed for six days, invisible to both
    # checks (CHANGELOG 2026-08-24).
    indexed_ids = {e["id"] for e in srcs}
    backlog_rows = []
    for r in scope.get("rules", []):
        if not r.get("in_scope") or r.get("default") != "#to-process":
            continue
        rp = str(r.get("path", ""))
        full = os.path.join(ROOT, rp)
        if not os.path.isdir(full):
            continue
        files = [os.path.relpath(f, ROOT) for f in glob.glob(os.path.join(full, "**/*.md"), recursive=True)]
        # Only count a file this rule actually governs; a more specific nested
        # rule may claim it instead (scope_of's longest-path precedence, CONTRACT §9).
        files = [f for f in files if scope_of(f, cfg) == "in"]
        missing = sorted(f for f in files if f not in indexed_ids)
        if missing:
            backlog_rows.append((rp, missing, len(files)))
    backlog_rows.sort(key=lambda r: -len(r[1]))

    # Oversized sources are split out of that backlog rather than left in it. A
    # folder default declares its files, so under the corrected phase 2 they are
    # PROCESS's to consolidate; but a 17,401-line manual cannot be read in one pass,
    # and the established answer is to process the person's own synthesis beside it
    # instead (the fire library, 2026-09-03: 401 and 128 lines carrying three
    # standards notes, against two 5,000-line manuals left unread). Listing them
    # separately is what stops the corrected rule from pointing an unattended cycle
    # at a document it cannot finish. The cut is far from anything real: every other
    # backlog file is under 800 lines and every oversized one is over 5,000.
    OVERSIZE_LINES = 1500

    def _lines(rel):
        try:
            with open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace") as fh:
                return sum(1 for _ in fh)
        except OSError:
            return 0
    oversized = []
    trimmed = []
    for rp, missing, total in backlog_rows:
        big = [(f, _lines(f)) for f in missing]
        keep = [f for f, n in big if n <= OVERSIZE_LINES]
        oversized += [(f, n) for f, n in big if n > OVERSIZE_LINES]
        if keep:
            trimmed.append((rp, keep, total))
    backlog_rows = trimmed
    oversized.sort(key=lambda r: -r[1])

    # touches. A path under an `in_scope: false` rule has been ruled on and drops out
    # of the report, so an answered folder stops being re-asked; an ignored path was
    # never knowledge to begin with. Both used to read as undeclared, which is what
    # made a folder added today indistinguishable from one passed over for months.
    def undeclared(p):
        top = p.split("/")[0]
        if top.startswith(".") or top in ("augment_wiki", "augment_plugin"):
            return False
        return scope_of(p, cfg) == "undecided"
    undecl = [os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, "**/*.md"), recursive=True)]
    undecl = [p for p in undecl if undeclared(p)]
    fold = Counter(display_path(p, cfg).split("/")[0] for p in undecl)
    pending = undecided_folders(ROOT, cfg)

    H = ["# VERIFY / DREAM queue", "",
         f"Written by DREAM, read at VERIFY. A current-state dashboard, not a log: everything above `{MARK}` is regenerated every run from `index.jsonl` and is never stale. The judgement items and the previous run's log below are curated.", "",
         f"Last regenerated: {STAMP}", "",
         "## Harvest (generated)", "",
         "Decision-harvest scope (`harvest.paths`): files processed of total per folder, most incomplete first. Read at the top of every sweep.", ""]
    if hrows:
        for rem, done, alln, label in hrows:
            H.append(f"- {done:>4}/{alln:<4}  `{label}`" + ("" if rem else "  (complete)"))
        H.append(f"- **{htot_done}/{htot_all} processed, {htot_all - htot_done} remaining** across {len(hrows)} harvest folders.")
    else:
        H.append("No harvest folders resolved from `harvest.paths`.")
    H += ["", "## Declared-folder backlog (generated)", "",
          "In-scope `#to-process` folders carrying `.md` files with no entry in `index.jsonl` at all, "
          "never touched by any pass. `detect_changes.py` and the Harvest section above cannot see this: "
          "both compare against files already indexed, so a folder declared but never actually processed "
          "is invisible to either. A file listed here has not been read by PROCESS or harvested. **This is a "
          "work queue, not a decision owed**: its folder's `default:` already declared it, so it is PROCESS's "
          "to consolidate, and it stays listed only until a pass reads it. A file that should not be swept in "
          "despite the default needs an explicit tag, which always wins over it (CONTRACT §9)."]
    if backlog_rows:
        H.append("")
        for rp, missing, total in backlog_rows:
            H.append(f"- {len(missing):>4}/{total:<4}  `{rp}`")
            for f in missing[:5]:
                H.append(f"    - `{f}`")
            if len(missing) > 5:
                H.append(f"    - (+{len(missing) - 5} more)")
    else:
        H.append("")
        H.append("None: every in-scope `#to-process` folder has at least started PROCESS on its files.")
    H += ["", "## Oversized, held back from that backlog (generated)", "",
          f"Declared sources over {OVERSIZE_LINES} lines, too large for one PROCESS pass. Held back rather "
          "than queued: the established treatment is to process the person's own condensed synthesis beside "
          "the document instead, which is what the fire library demonstrated on 2026-09-03. A file leaves "
          "this list by being synthesised, or by the person deciding it should be read whole."]
    if oversized:
        H.append("")
        for f, n in oversized:
            H.append(f"- {n:>6} lines  `{f}`")
    else:
        H.append("")
        H.append("None.")
    H += ["",
         "## State (generated)", "",
         f"- Wiki: {len(notes)} notes ({', '.join(f'{v} {k}' for k, v in sorted(typ.items()))}); status {', '.join(f'{v} {k}' for k, v in st.items())}.",
         f"- Sources indexed: {len(srcs)}. Processed-but-unlinked (`produced: []`): {len(unlinked)}.",
         "- Scope:"]
    for r in scope.get("rules", []):
        H.append(f"    - {'IN ' if r.get('in_scope') else 'OUT'} {r.get('default', ''):11} `{r['path']}`")
    H += ["", "## Health (generated)", "",
          f"- Flag rate (`#flagged` notes): {st.get('#flagged', 0)}. Zero means untested unless the wiki is being queried, not verified.",
          f"- Stale backlog: {st.get('#stale', 0)} ({100 * st.get('#stale', 0) / max(len(notes), 1):.0f}%).",
          f"- Processed-but-unlinked sources: {len(unlinked)} (findable via the `sources` view).",
          "", "## Folders awaiting a decision (generated)", ""]
    if pending:
        H.append("Top-level folders no scope rule touches. Each needs one answer at VERIFY step 1, "
                 "in scope with a default or `in_scope: false`; either way it leaves this list and "
                 "is not asked again, so what remains here is genuinely unanswered.")
        H.append("")
        for name, n in sorted(pending, key=lambda x: -x[1]):
            H.append(f"- {n:4}  `{name}`")
    else:
        H.append("None: every folder has been ruled on. A new one appears here at the next sweep.")
    H += ["", "## Undeclared census (generated)", "",
          f"Total undeclared `.md` (no rule touches them): {len(undecl)}. "
          f"Ruled-out and ignored paths are excluded.", ""]
    for k, v in fold.most_common(15):
        H.append(f"- {v:4}  `{k}`")

    # Applied unattended (generated). DREAM writes its own convergence, anchoring and
    # minting verdicts now (CONTRACT §12), and the trade that allows it is that every
    # one of them is read at the next sweep. That audit is generated here rather than
    # written into the queue by the cycle, for the same reason Harvest and Health are:
    # a section the run has to remember to write is a section that is eventually not
    # written, and this one going missing would leave autonomous writes with no reader
    # at all. Scoped to writes since the last recorded sweep, since that is what the
    # person has not yet seen.
    hist = os.path.join(ROOT, "augment_wiki/history.jsonl")
    applied, last_verify = [], ""
    if os.path.exists(hist):
        recs = []
        for line in open(hist, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except ValueError:
                continue
        # Position, not date (matches conformance.py's autonomy audit; fixed together
        # 2026-09-16). history.jsonl is append-only and strictly ordered, so "since the
        # last sweep" is "after the last verify_run marker in file order", not a date
        # comparison: a same-day DREAM run after a same-day VERIFY shares that marker's
        # YYYY-MM-DD, and a date-truncated comparison silently dropped it.
        last_verify_idx = -1
        for i, r in enumerate(recs):
            if str(r.get("kind", "")) == "verify_run":
                last_verify_idx = i
                last_verify = str(r.get("id", ""))
        for i, r in enumerate(recs):
            if not r.get("auto") or i <= last_verify_idx:
                continue
            applied.append((str(r.get("run", "")),
                            os.path.splitext(os.path.basename(str(r.get("id", ""))))[0],
                            str(r.get("note", ""))))
    H += ["", "## Applied unattended (generated)", "",
          "Every write DREAM made on its own judgement since the last recorded sweep "
          "(CONTRACT §12), newest run last. This is the audit: read the lines, and lift "
          "anything wrong back out with `undo_run.py . <run-id>`, or `--only slugA::slugB` "
          "for a single write. A revert is recorded as an ordinary confirmed removal.", ""]
    if applied:
        for rid, slug, note in applied:
            H.append(f"- `{slug}`: {note}  [{rid}]")
    else:
        H.append("None since the last sweep." if last_verify else
                 "None recorded. The cycle has written nothing unattended yet.")
    H += ["", ""]

    # Match the marker only as a heading at line start, never its mention inside
    # the generated intro text, or re-running would duplicate the header.
    tail = ""
    if os.path.exists(QUEUE):
        s = open(QUEUE, encoding="utf-8").read()
        m = re.search(r"(?m)^" + re.escape(MARK) + r"\s*$", s)
        if m:
            tail = s[m.start():]
    if not tail:
        tail = MARK + "\n\n(none)\n"
    open(QUEUE, "w", encoding="utf-8").write("\n".join(H) + tail)
    backlog_total = sum(len(missing) for _, missing, _ in backlog_rows)
    print(f"verify-queue header regenerated: {len(notes)} notes, {len(unlinked)} unlinked, "
          f"{len(undecl)} undeclared, {len(pending)} folders awaiting a decision, "
          f"{backlog_total} unindexed in declared folders")

if __name__ == "__main__":
    main()
