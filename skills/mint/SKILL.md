---
name: mint
description: Generate one specific wiki node the person names, a concept, entity or theme, and wire it into the graph. Use when someone asks to mint or create a note for a topic, says a concept is conspicuously missing, or wants a topic anchored deliberately rather than waiting for it to surface. Also runs unattended inside the nightly cycle when a cluster has grown around a node nobody wrote.
---

# Mint

**The top-down counterpart to `process`.** That skill consolidates sources bottom-up and writes whatever notes they yield; this one starts from a node the person knows should exist but that consolidation has not produced, then goes and finds the sources and the relations for it.

Confirm the tier before anything else, as `rules/surfaces.md` sets out: trust the session-start line in Code and Cowork, probe once per conversation in Chat, and stop and ask the person to connect when no tier is reachable. In Tier 2 every script call, file operation and git step below goes through that rule's table.

Read `reference/note-shape.md` and `reference/links.md` before writing, and `rules/write-flow.md` as duties. Run the freshness check first.

**One trigger arrives without the person, and the cycle acts on it without asking.** Where the nightly cycle reports an oversized anchor, a content note that seven or more notes already keyword-tag and whose members hang together, the cluster is gathering around a node nobody has written. That is this skill arriving bottom-up, answered the same way as a named request. **Unattended minting softens no guard**: no source, no node, and a node that cannot pass pre-flight is reported rather than written. The autonomy is over when the node gets made, never over what may be asserted in it.

## Duties in force

- **Nothing unsourced.** A concept or entity note is a claim, so every sentence cites a source. Being requested does not lower the bar.
- **A missing node with no source is not minted.** If nothing in the sources establishes the concept, say so and stop. Do not compose a plausible note. A **theme** is the one node that may be minted unsourced, because it asserts nothing.
- **Reject empty labels**, never resolve a contradiction, and keep the one house language.

## Steps

**1. Classify the node**, because the type dictates the sourcing rule. A **concept** is a sourced idea, of kind principle, method, model, metric, standard, claim or procedure. An **entity** is a sourced person, place, organisation, product, tool or project. A **theme** is an unsourced topical anchor, minted only when several notes already reach for the topic.

A node with a real claim to make is a concept; a node that only gathers other notes is a theme. Where both are true, the sourced claim is the concept and the theme is the bare anchor beside it.

**2. Existence check first.** Confirm the node does not already exist under another name. If it does, stop and point to it rather than minting a near-duplicate. This is the judgement most worth the thinking, since it decides conceptual identity rather than string similarity.

**3. Establish it from the sources.** Look past the wiki: reach the source layer through the `sources` view and read the actual files, including the processed-but-unlinked ones, because the material establishing a requested node is often exactly what no earlier consolidation extracted. Assemble the body from what those sources say, every sentence cited. Skip this step for a theme.

**4. Write the node.** A concept or entity takes the full note shape with its citation list. A theme takes the stub, frontmatter and title only, with the member list left to the generator.

**5. Find and wire the relations.** This is the half that makes the skill worth having. Scan the wiki for related notes, descending into their sources where the relation is not decidable from the wiki alone, and choose the tier per `reference/links.md`: a **sourced link** where a source states the connection, carrying its reason and citation; a **keyword tag** where the relation is a real adjacency no single source asserts. For a theme, the wiring is the step: add the theme to each member's keywords, then rebuild the theme body.

**Where the node was minted for a cluster, propose what it absorbs.** Pairwise tags saying no more than what the new node now carries are replaced by membership in it; a tag saying something the node does not carry stays. Judge this **per tag, defaulting to absorb**, never as a blanket sweep. Absorption is a removal, the one thing this system takes away, and a tidy-looking sweep is how a real finding disappears. Each removal is confirmed at the sweep.

**6. Bookkeeping.** Append the node and any rebuilt note to history, recompact the index, run conformance, regenerate the views, theme bodies and hubs. A minted note that gave an existing note a new source marks that note `#stale` like any input change.

**Where minting resolved a standing convergence pair rather than ruling on its bare tag, dismiss that pair in the same run.** Such a pair never got an explicit verdict, so nothing stops it re-ranking into a later priority lane and costing a second read for a question already answered.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/dismiss_pairs.py" <vault> --note "resolved by minting <node>" slugA::slugB
```

## Never

- Mint a concept or entity with no source. Absence of a source is absence of the note.
- Fabricate a link to make the node look connected. An unwired but sourced node is fine; a plausible unsourced link is a defect.
- Resolve a contradiction the wiring exposes. Open a tension note and queue it.
- Edit a source, or mint from an `#excluded` or undeclared one.
