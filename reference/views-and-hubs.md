# Hubs, views, and the autonomy line

## Hubs

**A hub is generated, so it is never hand-edited: an edit is overwritten on the next build.** Corrections belong to the notes a hub indexes, never to the hub.

A hub indexes a slice of the wiki. Hubs live in `hub/`, one per type value and one per kind value, plus `hub/hub.md` which indexes the hubs and lists the views. Their basenames are exactly the type and kind names, which is what lets `type: "[[concept]]"` and `kind: "[[project]]"` on a note resolve to them regardless of which subfolder holds the file.

Each holds an alphabetic index of its members, grouped by first letter of the title with articles ignored for sorting, extracted mechanically from the index. A note appears in its type hub and its kind hub at once, so a project entity is listed under both. Hubs carry no prose beyond a one-line description, and regenerating them is a mechanical phase needing no model call.

**A hub cites no source, and that is not an orphan condition.** A hub is a derived index of other notes rather than a compiled claim, so the every-note-cites-a-source rule does not apply and hubs are excluded from the conformance passes requiring citations.

Themes are the one hub-like thing that is curated rather than automatic. `hub/theme.md` is the type hub listing every theme, while each theme note is itself the anchor a cluster points at through its keywords.

## Views

**A view proposes; it never writes into a note by itself.** Like a hub it is generated, so a hand edit does not survive.

A view presents the wiki along an axis the note graph does not carry. It shares the hub's discipline, compiled mechanically, regenerated wholesale, never hand-edited, exempt from the citation passes, and differs only in what it draws: a hub lists the members of one type or kind, a view draws a relation across notes. A view declares `type: "[[hub]]"`, lives in `view/`, and is listed in the hub index. It is always regenerated, and **written even when empty, so its link never dangles.** Three are defined.

### relations

Surfaces adjacencies between notes that no single source asserted, so the graph can grow past what any one source happens to state. It ranks unlinked pairs by content similarity in a **convergent** lane, the strongest pairs overall, and a **coverage** lane, each note's own strongest tie; proposes **memberships** for anchors and a theme where a cluster has none; lists existing contradictions as a **divergent** lane of standing tension candidates; and runs a **decay** lane backwards over the existing keyword edges of notes recompiled that cycle, proposing removal where two notes now share almost no content, because a source rewrite can take away what an edge was written for and nothing else ever looks back at one.

**How the ranking is computed is generator mechanism and is documented at the script**, not here. Those are tuned numbers, and a rule that had to be amended to change a weight would either stop being amended or stop being true.

What this file fixes is what the view may do.

**The cycle writes what it adds and asks about what it takes away.** An added keyword tag asserts nothing, is recoverable by removing it, and was being confirmed at a rate that made the confirmation ceremonial. So the cycle applies its own convergence and anchoring verdicts, and mints the node a cluster deserves, without waiting. **A removal still reaches the person**, because it is the one operation that destroys rather than adds and the only one git alone can recover; so does anything touching the source layer, a tension note, and a supersession. The rate governing autonomy is not throughput but auditability: every convergence tag, anchor and mint carries `auto: true` and its run id in history, the report names each one on a line, and one command lifts a night back out.

**Ordinary compilation (EXTEND, REBUILD) does not carry the marker.** It was unattended before this autonomy regime existed and is not the surface CONTRACT §12 was built to audit; `compiled:` already stamps the date on every rebuild, which is what a person checking "when was this last processed" actually needs. Marking it too would put routine consolidation on the same audit list as a judgement call, burying the one the marker exists to surface.

**What a confirmed candidate becomes is decided by the ladder in `links.md`, not here.** The view ranks and surfaces; the ladder rules on what the surfaced thing is. Shared vocabulary, a co-citation, a shared kind or a shared topic are what surfaced a candidate, never grounds for linking it.

**A promotion the cycle is sure of reaches the note that night; one it is unsure of reaches the report.** The three-way verdict is the gate, and it is the model's reading rather than a score: apply, hold, or dismiss. Holding is not a delay to be minimised, it is what the autonomy is bought with, so a candidate the cycle cannot argue for in one sentence is held. The cycle may still decline on its own, because declining writes nothing into the graph.

A declined pair is recorded in the dismissal sidecar and never resurfaces. A declined **removal** goes to the same file marked as a keep, read into a separate set, since declining to create an edge and declining to destroy one are opposite answers about one pair. That sidecar is tooling state and stays out of the index and the history, which hold vault state only.

**Removal is the person's, and is the one exception to never delete.** Promotion is no longer confirmed at all, so removal is the only edge operation that waits, and the asymmetry is the point: a wrong add is answered by the next decay pass or by the undo script, while a wrong removal leaves nothing behind to notice it. Everything else in this system supersedes rather than deletes, because what it holds is a statement someone can be shown to have made. A keyword tag makes no statement, so there is nothing to supersede: it is dropped outright, only at the sweep, only by the person, and only through the script, with git and the note's history entry holding what was removed. **A sourced link is not removed this way at all**; it is re-derived by the rebuild that recompiles the note, which is a recompilation rather than a deletion.

**An anchor is any note two or more notes already keyword-tag**, not only a theme, so membership proposals are general across the types. This is what keeps an anchor gathering everything about its topic rather than only what was hand-tagged when it was minted, and it is why membership is a standing proposal each sweep rather than a one-time act at minting.

**Some candidates never enter the net at all**, excluded structurally rather than by dismissal: a pair already joined by a sourced link, the two positions a tension note links through its headings, and a pair the subsumption clauses already answer. A structural exclusion is a **recall** decision and never a judgement one: it stops generating what the person has repeatedly said is not worth their time, and an uncertain candidate, including one leaning toward rejection, is still proposed.

**A cluster is proposed as an anchor, not as its pairs.** Where one note carries three or more of the pairs a slice would draw, the view reports it as a cluster ahead of those pairs, because minting or joining an anchor answers all of them at once.

The wiki is monolingual, and conceptual identity across languages is settled upstream where meaning is read directly, never by asking a term-overlap measure to bridge a language it cannot see.

These rules bind wherever the overlay is worked. The cycle states only when a pass is owed and how large a slice it takes; the sweep states only how proposals are presented and applied. Neither restates the rules above.

### timeline

A per-project chronology, aggregating the decisions block of every project entity into one dated view, grouped by project and ordered in time.

A project entity may carry a **decisions block**, a dated and sourced list:

```markdown
## Decisions
- 2024-05-26, tooling: model origin set to the survey point so exports land at the right level. [[12.06 coordination-note]]
- 2024-06-14, design: timber structure chosen over concrete, for its lower embodied carbon. [[12.09 design-review]]
```

Each line reads `date, tag: one-line decision. [[source]]`, the tag being one of `design`, `tooling`, `practice`, `bid`. The line is a sourced sentence like any other: the decision and its reason come from the cited log, never reconstructed, and where the log records a choice but not its reason the reason is left out. **A decision is deliberately not a note of its own**, because one note per decision would sprawl the wiki with entries carrying no standalone meaning. The value is in the sequence, and the sequence is a view.

The block is populated by the harvest mode, the one thing processed out of a project's routine logs, whose concept yield is otherwise too low to justify processing them.

**A rebuild preserves the decisions block.** The block is harvested rather than compiled, its lines citing project logs that are not body sources, so a rebuild recompiles the body prose from the entity's description and feasibility sources only and carries the block through untouched. Harvesting therefore leaves the entity current rather than stale, since there is no body to recompile. For the same reason the conformance passes treat a decision line's link as a source citation resolving to a source file, not as a relationship target that must resolve to a wiki note.

### sources

An index into the source layer, grouping every processed source under its project or library context, marking whether a wiki note cites it, and linking each context to the notes it produced.

It exists because **the wiki is a point of entry into the sources, not a wall around them.** A general question is usually answered from the notes; a detailed one is answered by descending into the sources they cite and the other sources in the same context, including the processed-but-unlinked ones that no concept was extracted from but that still hold the detail. The reading skills rely on this view to reach that material, and it gives the unlinked sources a home so they are retrievable and tied to their context rather than findable only by scanning the index.

Its section headings are the context names alone, which makes them **stable link anchors**. A project note back-links to its own section through `further_sources:`, pointing at all the source material in its context including the files not processed into a note. This is written once and stays current on its own: the anchor never changes while the section behind it is regenerated every cycle, so the pointer is maintained in one place rather than as lists copied across many notes. A rebuild preserves `further_sources:` as it preserves the decisions block.
