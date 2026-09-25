---
name: dream
description: The nightly maintenance cycle. Use when the person asks to run the cycle, asks what needs attention, asks about the backlog, or when scheduled unattended. Detects changed sources, rebuilds what went stale, consolidates new material, runs the checks, anchors and connects the notes it wrote, regenerates the views, and reports to the queue the sweep reads.
---

# Dream

Scheduled, unattended maintenance. It absorbs what were separately a backlog consolidation and a lint pass, because they share a cadence, a queue and a report. **Its character is consolidation, not depletion**: it takes in what has changed and settles the derived layer around it, night after night.

Runs nightly or on demand. It does the machine work; `verify`, weekly, does the human work, and this skill's queue is what that sweep reads.

Confirm the tier before anything else, as `rules/surfaces.md` sets out: trust the session-start line in Code and Cowork, probe once per conversation in Chat, and stop and ask the person to connect when no tier is reachable. In Tier 2 every script call, file operation and git step below goes through that rule's table.

Read `reference/scope-and-index.md`, `reference/statuses.md`, `reference/links.md` and `reference/views-and-hubs.md`, plus all three files in `rules/`. Run the freshness check first.

## Duties in force

- **Append, never blank.** Supersede in place. Never delete.
- **Never launder confidence.** Report the state as it is, including when it is deteriorating.
- **Fidelity, not correction.** An apparent error in a source is logged for the person, never fixed.

## What it may do alone, and what it must queue

The dividing line is reversibility, not difficulty. Judgement alone does not send work to the queue, since the cycle's judgement is what the system is for. **What sends work to the queue is a write the person cannot cheaply undo.**

**Autonomous**, because each is recoverable: detecting changed inputs, tagging stale, rebuilding stale notes, running the checks, compacting the index, appending to history, anchoring the notes this cycle wrote, applying the convergence verdicts it is sure of, and minting the node a cluster deserves. Every one of those writes carries its run id in the ledger, is named on one line of the report, and comes back out with `undo_run.py`.

**Queued for the sweep**, because each destroys, asserts a conflict, or reaches the person's own layer: removing any edge, merging near-duplicates, splitting a note that rebuilds every cycle, superseding or retiring a note, opening a tension note, acting on an observation about a source, and anything at all touching the source layer. A convergence candidate the cycle cannot argue for in one sentence is queued too, and holding it is not a failure of the automation but the thing that pays for it.

Deletion is available to neither.

## Phases

Run in order. Each phase writes to history as it goes, so an interrupted run resumes from the last completed item rather than from the beginning.

**1. Detect changed inputs.** Compare every indexed source's current content hash against the stored one. Declaring or retagging a source is not an edit and must not trigger a rebuild. Where a hash differs, mark every note compiled from that source `#stale`. This runs first because everything downstream depends on knowing what moved.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/detect_changes.py" <vault>
```

Use the pinned script rather than a hand pass, which miscounts, and rather than a reimplemented hash, which raises false staleness.

**A missing file is queued, never resolved by the cycle.** Where an indexed source has no file, report it and stop there. Whether the person deleted it deliberately or a sync dropped it is exactly the judgement the cycle cannot make, and guessing either way is costly: recording a lost note as an intended deletion buries a real failure, and treating an intended deletion as a fault re-reports it every night. A source already recorded deleted is not a finding and is not reported again.

**A `#processed` source that drifts with `produced: []` has nothing to mark `#stale`, and no other rule reaches it either.** The drift rule above only fires a rebuild when `produced` is non-empty; an explicit `#processed` tag sits outside phase 3's `#to-process` scope regardless of what the content now says, so a source PROCESS read and found nothing in stays invisible to every later drift on it too, forever, unless someone happens to remember. Always re-examine the changed content for extraction-worthiness on this class of drift, and always re-stamp the hash regardless of the verdict, whether or not anything comes of it, so the source stops re-reporting as unread drift. Where the re-read argues for a full pass rather than a one-off read (recurring genuine material, not noise), report it for VERIFY to re-tag `#to-process` rather than deciding that alone.

**2. Count what is undeclared, and name what has never been asked about.** Count sources that **resolve** to no status, which is not the same as carrying no tag: a folder rule with a default has already decided for every file under it, so an untagged file there is declared. What belongs in this census is a source no rule reaches. Carry the count into the report so an untouched archive announces itself rather than sitting silent.

The declared-folder backlog is therefore a work queue rather than a decision owed: files under a `#to-process` default that no pass has read yet. Reporting them is not a substitute for processing them. Where a file should not be swept in despite its folder's default, the way to say so is an explicit tag on that file, which always wins over the default.

Report separately the folders awaiting a decision, the top-level folders no scope rule touches. **That list is a decision owed, not a statistic**: a folder added this week and one passed over months ago are the same number in a census and completely different questions. Naming them is all the cycle may do.

**3. Consolidate.** Process sources resolving to `#to-process`, and only those, working until the session budget is reached rather than stopping at an arbitrary count.

Three limits govern this and conflating them is what produces a fixed batch size. **Transaction** is one source: process it, append its history lines, move on. This never changes, because it is what makes an interrupted run cost at most one item; the history append is per source and must never be batched to the end of a run, since the index can be rebuilt from history but a history line not yet written is work an interruption loses outright. **Merge interval** is how many sources may be processed before duplicate detection runs, kept near fifteen while the wiki is small and raised only once the duplicate rate has actually fallen. **Session budget** is how much a single run attempts: use most of the session, stopping around ninety percent and checkpointing cleanly rather than being cut off mid-item.

**Decision-harvest runs in this phase too**, over the project logs declared for it whose owning entity exists, obeying the same three limits. A harvest log whose project has no entity is skipped and reported, never harvested into thin air. This is what makes declaring a project for harvest actually run on its own, since the `#to-process` reading never picks up an untagged harvest log.

**Harvest is not subject to the rate discipline below, and the cycle never withholds it of its own accord.** That discipline throttles concept consolidation, because synthesis produced faster than the person reviews it accumulates unreviewed. Harvest extracts dated, source-cited decisions and mints no concept, so there is no synthesis to outrun review. Work the declared logs to the session budget every run; a large remaining backlog is a reason to keep harvesting, not to pause.

**4. Rebuild.** Recompile stale notes and hubs at or past their threshold, re-running pre-flight on each and setting `#current` only if it passes. Where a note was rebuilt because its source changed, **re-stamp that source's index entry** to its current hash and date, or the source stays flagged as drift on every later detect pass and its notes re-stale needlessly.

**A rebuild re-derives the note's edges; it never carries them forward unread.** A source rewrite can take away what an edge was written for, and a rebuild copying the old links across preserves a claim the new body no longer makes. So for each rebuilt note, re-derive the **sourced links** from the rebuilt body and the sources open in front of you: an entry whose cited source no longer states the connection, or whose reason the rebuilt body now contradicts, is not re-emitted, and where the connection survives in narrowed form the reason is rewritten to what the source now supports rather than the link being dropped. **Keyword tags are never dropped by the cycle**, since they were promoted by the person and an unsourced tag says only that two notes are worth reading together, which a narrowed claim rarely destroys; where the rebuild leaves a tag with nothing behind it, queue it as a removal proposal and leave it in place meanwhile.

**4b. Restyle batch**, while that queue has anything pending and skipped entirely when it does not. The status call answers it in one line.

**4c. Compact.** Rewrite the index from history with the pinned script, never in place and never by hand.

**It sits here rather than at phase 7, because phases 5 and 6 read the index and cannot see this cycle's own work until it runs.** Phases 3, 4 and 4b are the only ones writing note entries to history; phase 5 checks, phase 6 writes to the queue and the sidecar, and phase 8 reports. One call here serves every later phase.

**5. Conformance.** Catches what a partial or interrupted run left behind. Two scripts carry the whole mechanical set, and **what they check is documented at the scripts rather than restated here**, since a prose list beside a pinned implementation is a second source of truth that drifts.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/conformance.py" <vault>
```

Defects fail the run and are reported first; advisories are surfaced to the sweep.

One check in this phase is not mechanical and no script reaches it: **unsupported entity content**, an entity note asserting background no cited source establishes. This is fabrication wearing a reference-work costume, and it is the failure mode entity notes invite, so read the entity notes rebuilt this cycle against their sources rather than trusting a clean script run to mean it did not happen.

**6. Enrichment.** The work that benefits from running while nobody is waiting.

**Anchoring first, over the notes this cycle wrote.** The anchor list gives, for each note compiled tonight, the anchors whose members it matches above the membership floor, ranked, five at most. Read them and attach the note to the ones it genuinely belongs to, applying the tag in the same pass. This runs before the slice below because it is the phase's highest-value work: a note compiled tonight used to sit unanchored until it happened to rank inside a twenty-item slice, which for a peripheral note could take many sweeps. **Attach to what the note is about, not to everything it grazes.** A note matching five anchors is usually a note with a broad subject, and three of those five will be buckets; the cap is a reading bound, not a target to fill.

**Convergence overlay.** The relations view ranks unlinked pairs into a reproducible candidate net, and `reference/links.md` governs what any of them may become. What this phase decides is how much of the net a cycle works and which verdicts it writes rather than reports.

The pass runs every cycle and what bounds it is **the slice, a fixed twenty items**, drawn in a fixed order of precedence. **Oversized anchors first, then clusters, before any pair is judged**: where a content note is already keyword-tagged by seven or more notes that hang together, read the members rather than their scores, because the cosine says these notes sit near each other and only reading says what they sit near. Then mint the missing node, split the overloaded note into its claim plus a bare anchor, or leave it. Minting is autonomous and the sourcing rule does not relax for it; splitting is queued, because it rewrites a note that already says something; and the absorption a mint implies is queued, because absorbing a tag is a removal. A cluster, one note carrying three or more of the slice's pairs, is an anchor question answered before the pairs it would absorb, which are then not also judged.

**Then the priority lane to exhaustion**, every candidate touching a note compiled in the last week, pairs before memberships, strongest first. Freshly processed material is where a proposal is worth most, because the person can still judge it against a source they remember, and where the ranking serves it worst, since a note compiled today enters a net of hundreds and sorts on cosine like any other. Read the full lane from the script rather than the view, which caps its display for readability.

**Then the backlog**, filling whatever remains of the twenty, weighted roughly sixty percent coverage to forty percent convergent so the harvest widens across the graph instead of deepening one corner. Against a net this large a slice of twenty is a many-sweep burn-down, and the report says so plainly rather than letting the scale go unstated. The cosine only orders what is read first, so judge the candidates semantically, catching the paraphrase and synonymy the ranking misses, and scan titles and opening glosses as a recall net.

**Apply what you can argue for; hold what you cannot.** The verdict is three-way: apply, hold, or dismiss. A candidate whose reason the cycle can state in one sentence is applied tonight. One that needs the person's own knowledge to settle, that turns on whether a source says something the cycle cannot check, or that the cycle finds itself arguing both sides of, is **held** and listed in the report as an open question. **Holding is not a delay to be minimised. It is what buys the autonomy**, and a cycle that holds nothing over many runs is not being careful, it is being careless faster.

Write every verdict through the script and give it a reason, never by hand: a cycle applying twenty tags and then hand-writing twenty ledger lines will eventually write nineteen.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/apply_keywords.py" <vault> --auto --run <run-id> --reason "why this pair, in one sentence" slugA::slugB
```

Write each tag in one direction, naming the note that gains it, since a keyword is directional by default; the symmetric case is real but the exception and is argued rather than assumed.

A pair the cycle rules out, or that the sweep declines, is appended to the dismissal sidecar so it is judged once and never resurfaces. The same file carries the opposite verdict, a declined removal, and the two are read into separate sets, since declining to create an edge and declining to destroy one are opposite answers about one pair and must not cancel.

**Also in this phase**: near-duplicate detection queued as merge candidates; contradiction detection proposing a tension note; the decay lane, read after phase 7 when the overlay has today's rebuilds in it, queued as removal proposals rather than applied; chronic rebuild, notes recompiling every cycle, queued as split candidates; unstable synthesis, notes whose body changes materially without their sources changing, exempt under a restyle marker; and the counts of undeclared sources and of sources that produced nothing, a rising figure in the latter being evidence the consolidation is not earning its keep.

**7. Regenerate.** The index is already current, so this phase only rebuilds the hubs, views and theme bodies from it: the views first, then each theme's member list from the keyword back-references, then the hubs. All of it is mechanical and overwrites its output wholesale, so a hand edit to a hub, a view or a theme body does not survive. Theme notes are never created or deleted here, since minting and retiring a theme are curation decisions; the script only refills the bodies of themes that exist. A view is written even when empty, so its link never dangles.

Then bring the sources' backlink lines into step with the compacted index, so a source that gained, lost or changed a citing note tonight says so in its own frontmatter by morning. This writes into the source layer, and is autonomous only because it is the same class of write as the status tag: frontmatter only, a mirror of the index rather than a judgement, and refused by the script wherever it would move a content hash.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sync_backlinks.py" <vault>
```

**8. Report.** A grouped list for the sweep, critical errors first, then conformance, then **what the cycle wrote unattended**, then the rest, each finding with its proposed action and enough context to decide without opening the file. No prose.

**The applied-writes section is the audit surface, and it is not optional.** One line per autonomous write, naming the note that gained the tag, what it gained and the one-sentence reason, under the run id the undo script takes. The person's work at the sweep is to scan those lines and say undo that one, which is strictly less than approving each in advance and is the only thing standing between an autonomous cycle and a graph nobody is reading. **A cycle that applies writes and does not list them has broken the trade that let it apply them at all.**

A critical error is anything the run could not complete or that risked the source layer: a failed or aborted write, a source whose content the run changed even inadvertently, a hash drift with no matching edit, or a phase that could not run. These are reported whether or not they were recovered in the same run, because a silently recovered near-miss is exactly what must still reach the person.

**One item is at most two lines and carries an id**, as `<ID> | the finding, in one sentence | the proposed action`. This is the rule the report breaks most often, and the failure compounds: a finding written as a paragraph cannot be scanned, so it is not decided, so it is carried to the next sweep, until the queue outgrows the sweep's own time budget. The narrative belongs in history, which is the permanent record.

The report is a **current-state dashboard, not an append log**, and must never accumulate stale information. Its generated header is rebuilt each run. The judgement tail below it is curated: reconcile it item by item every run, dropping what the sweep resolved and adding what this run surfaced. **Never by replacing a span of prose**, since a span replacement cannot tell an item it means to resolve from one that merely sits next to it, and once dropped an unanswered item is gone from the only file holding it. The one thing allowed to be historical is a short previous-run log; older logs are dropped.

**Re-check drift immediately before the push.** A cycle pulls at the start and pushes at the end, and on a machine the owner also syncs to, that gap is long enough for a concurrent commit to land after phase 1 declared what changed. Run the detect script once more before committing, and fold in anything new. Treat a push rejection as exactly this signal, never as a reason to force-push or retry blindly: re-pull, re-detect, rebuild what the incoming commit drifted, then push.

## Self-improvement

A critical finding is not only reported, it is analysed into a proposed fix. Where one reveals a defect in the system itself, draft the change and queue it for sign-off at the sweep. It is not integrated automatically, because a wrong self-edit would propagate silently through every later run. What is autonomous is the detection and the proposal, never the edit.

**The trigger is not only a critical finding.** A defect can be small and still real: a stale path in a deployed file, a mechanical step done by hand for want of a script, a check that flags what it should not, a bookkeeping id that collides. These surface while the work is being done rather than as a phase's pass or fail, so without a home they get routed around in the moment and then persist run after run. Any friction noticed in any operation is recorded to the standing system-observations list, kept distinct from the content queue, each with what, where, and a proposed fix. **The bar to record is deliberately low; the bar to change is unchanged.**

**Record it in that list and nowhere else.** An idea mentioned only in a run-log entry has not been proposed, it has been buried, because the decision is taken by walking the list. Lift it into the list in the same run rather than leaving it where it surfaced.

Fix at the cause rather than the symptom, per `rules/cognition.md` §6: ask why the existing rule did not hold and what else shares that cause, and prefer a check to a restatement.

## Not a finding

**Notes with no inbound links are normal.** A concept note is connected through its sources by construction. Isolation is not a defect and must not be reported as one.

## Where reasoning is spent

Mechanical work belongs in code: hash comparison, counting, conformance parsing, index compaction and report assembly are deterministic, and a model call that recomputes a hash is waste that can also get it subtly wrong in a way a script cannot.

Judgement work is where thinking earns its cost: extraction, deduplication, the existence check, classification, rebuilding a body from several sources, and contradiction detection. Every failure mode in `rules/cognition.md` §3 lives there, and none of them is a knowledge failure that could be looked up.

## Rate

The limit is not throughput but how much the person can read and correct. **For the convergence pass this means the audit, not the queue**: the writes land tonight, and what must stay inside the reading budget is the list of them at the next sweep, which is why the slice is a fixed twenty rather than whatever the net holds. For consolidation the older rule stands: queue what the next sweep can absorb and let the cycle idle. A run that finishes early is working correctly. Harvest is exempt.

After the first batch on a new archive, stop and ask whether the output is worth continuing, with roughly half the notes surviving without correction as the rough threshold. Well below it, propose narrowing the scope rather than processing the rest.

## Never

- Delete anything.
- Merge, split, or open a tension note without confirmation.
- Edit a source note, or act on an observation about one.
- Process an `#excluded` source, an undeclared source, or a folder not in scope.
- Infer intent from silence. An untagged source is a question, never an assumption.
- Continue past the first consolidation of a new archive without the person having seen the output.
- Raise the merge interval before the duplicate rate has actually fallen.
- Rewrite the index without going through history first.
- Batch history writes to the end of a run.
