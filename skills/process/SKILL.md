---
name: process
description: Compile source notes into wiki notes. Use when new sources are waiting, when the person asks to digest or process material, when a note's sources changed and it needs rebuilding, when project logs need their dated decisions harvested, or when the writing rules changed and existing notes need restyling. Runs without the person present, so every rule here is a hard constraint.
---

# Process

Reads sources that resolve to `#to-process`, writes wiki notes. **The one skill that runs with nobody watching, so every rule below is a constraint rather than a preference.**

Read `reference/note-shape.md`, `reference/links.md`, `reference/statuses.md` and `reference/scope-and-index.md`, plus `rules/write-flow.md` as duties. Run the freshness check first.

Four modes. **Extend** runs on every pass. **Rebuild** runs on notes whose input set changed. **Harvest** runs on project logs declared for it, pulling dated decisions into the project entity without minting concepts. **Restyle** runs when the writing rules change rather than the sources.

## Duties in force

- **Fidelity, not correction.** Represent what the source says, including where it appears wrong. Record the observation, never fix the text.
- **Nothing unsourced.** Every sentence, body or link context, cites a source.
- **One house language.** Sources may be in any language; the note compiled from them is written in the language recorded in `augment_wiki/config.yaml`. Translation is part of compilation, not a change to the source, whose title keeps its own language in the citation. Keeping the wiki monolingual is what settles conceptual identity across languages at the point where meaning is read directly, rather than leaving it to a downstream similarity measure that is blind to the same concept in another tongue.
- **Reject empty labels and redundancy.**
- **Never resolve a contradiction.** Open a tension note instead.

## Pre-flight, before writing anything

Verification is not a later pass. A note failing any of these is not written, and the failure is logged for the sweep.

1. Every link target exists, or is being created in this same pass. **A link to a note that does not exist is a fabrication**, not a placeholder.
2. Every link context carries its source.
3. Every link type is one of the three in `reference/links.md`.
4. The title is ten words or fewer.
5. The note cites at least one source.
6. The status tag is one of the defined set.

Checks 1 and 2 exist because a composed link reads exactly like a considered one, and nothing downstream can tell them apart.

## Extend

**1. Scope.** Sources resolving to `#to-process`, whether by explicit tag or folder default. A folder-default source carries no inline tag, so do not look for one. Skip `#excluded` unconditionally. The guard against reprocessing is the index, a matching hash and processed date, never the presence of a tag.

**2. Detect changed inputs first.** Compare each in-scope source's hash against the index; where it differs, mark every note compiled from it `#stale` and queue a rebuild. Do this before extracting anything.

**3. Extract atomic units.** The smallest indivisible thing worth a note, one per note. A unit is a concept (an idea, principle, method, procedure or claim) or an entity (a person, place, organisation, product, tool or project). Classify it, because type and kind decide the folder, the body shape and the test it must pass. Ordered, tool-bound how-to is a `procedure` concept carrying a steps block, not a prose `method`.

**4. Rank by significance, deduplicate, then shorten.** Merge overlapping items before writing anything.

**5. Reject label-only items.** A concept must state what the idea is and by what mechanism it works. An entity must state what role it plays in the archive and what it connects. A unit answering neither test is a label, so drop it. For entities, resist biography: only what a source establishes belongs in the note, and general knowledge no source supports is a fidelity breach. A source that only enumerates named tools or links rarely supports a standalone concept and usually contributes as a secondary source to an entity note.

**6. Check existence.** Search the wiki for the concept. Prefer extending an existing note over creating a near-duplicate. Where uncertain, say so rather than guessing, since a wrong merge costs more than a flagged doubt.

**7. Write or extend.** A new unit becomes a new note in its type's body shape, `#current`. An existing concept gaining a new source gets the citation added and is marked `#stale`, because its input set changed. A hub gaining a new source gets the link and an incremented unincorporated count, and is not marked stale.

**8. Write link contexts** in the shape `reference/links.md` gives, each with its source. If the reason cannot be traced to a source, do not write the link.

**9. Record observations.** Where a source appears factually wrong, internally inconsistent, or contradicted by another, log it for the sweep. Do not alter what the note says.

**10. Update the index** and mark the source `#processed`, with `#linked` where a note now cites it and `#unlinked` where none does.

## Rebuild

Runs on `#stale` notes and on hubs past their threshold.

Gather the union of all sources cited anywhere in the note and **rebuild the body from that union**. Preserve the title unless the concept genuinely moved, since a changed title breaks inbound links. Preserve any decisions block verbatim, because it is harvested rather than compiled, and any back-link into the sources view the same way.

Re-derive link contexts, dropping any whose source no longer supports them. Reset the note's compiled-from set and stamp it, and **re-stamp any source whose file hash changed** to its current hash and date, the same write made on first processing, so an edited source is not flagged as drift on the next detect pass and its notes are not re-staled needlessly.

Run pre-flight again and set `#current` only if it passes. **If the rebuilt body cannot hold the material coherently, do not force it**: report a split candidate and leave the note `#stale`.

## Harvest

Runs on project logs declared in scope for harvest, a narrower declaration than `#to-process`. It exists because those logs carry too little atomic concept to justify full processing but do carry decisions worth a chronology.

Locate the owning project entity. **If none exists there is nothing to harvest into**: report it and skip the log. Harvest never creates the project entity.

Extract dated decisions only, each as one line, `date, tag: one-line decision, [[log]]`, tagged `design`, `tooling`, `practice` or `bid`. The decision and its reason come from the log; where the log gives a choice but no reason, omit the reason rather than inventing one.

Merge into the entity's decisions block, appending lines not already present, keeping it sorted by date, and not duplicating a decision harvested from another log. Adding lines changes the entity's input set, so mark it `#stale` exactly as a new cited source would.

**Extract nothing else.** No concept, no method, no claim. If a log genuinely contains an atomic concept, that is an extend decision on a `#to-process` source and the log's scope must say so.

Mark the log `#processed #linked` if a decision was harvested, in its frontmatter. A log yielding no decision stays untagged and surfaces as producing nothing.

## Restyle

Runs when the **writing rules** change, not when a source does. Nothing else rebuilds a note whose style went out of date, only one whose sources moved, so without a deliberate pass every note written under superseded rules stays as written. It is rebuild under a different trigger, worked as a batched queue across consecutive cycles until empty.

**Not a reprocess.** The set of notes is fixed and so is each note's citation list. Restyle never re-derives which notes should exist, never runs extend over the source tree, and never touches the dismissal sidecar, the tension notes, the themes or a decisions block. Every sweep decision already in the vault stands.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/restyle_queue.py" <vault> status|init|next|done
```

Notes are **not** marked `#stale` to schedule them, since that status means a note's sources moved and borrowing it would make every later cycle report drift that does not exist.

Beyond rebuild's steps: the transaction is one note, written and logged and marked done before the next, since an interruption must cost at most one. **Rebuild from the sources, not from the existing prose**, which is the thing this pass exists to catch. Meaning is not the writer's to change: a rebuilt note may say the same things better, and may not add, remove, soften or strengthen a claim. Where the rebuild reveals the old note overstated or misread its sources, that is a finding carrying both readings, never a silent repair. Close the batch with a restyle marker in history, which is what stops the unstable-synthesis check misreading the pass.

## Cost discipline

Link resolution and backlink upkeep are mechanical, done by pattern matching with no model call. Only extraction, context-writing and rebuilding are semantic. The existence check deserves the most thinking, since it decides whether a concept already exists under another name, which is a judgement about conceptual identity rather than string similarity, and it is the single check standing between a backlog and a wiki full of near-duplicates.

## Never

- Write into the body of a source note. Setting its declaration is metadata and is permitted; nothing else in the source may be touched.
- Rewrite a source file to change its status. A status write edits the frontmatter block only, giving a bare-form file a fenced block if it needs one, and never reads and rewrites the body, whose bytes and newline convention the hash depends on.
- Process an `#excluded` source.
- Rewrite a body during extend. Mark it stale and let rebuild do it.
- Invent a link, or a link context, to fill a gap in the sources.
- Correct an error found in a source. Record it and move on.
