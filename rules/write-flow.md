# Write flow: how prose is written

`reference/note-shape.md` governs the shape of a note, `rules/cognition.md` the epistemic duties, this file the writing.

**Judgment before procedure.** The eight anchors decide what a piece of prose commits to; the rules after them are how that judgment is carried out. A rule list is satisfiable by prose that obeys every line and says nothing, which is the failure this file exists to prevent.

## 0. What this binds

Every piece of prose the model writes, in any language: wiki notes, generated bodies, callouts, any source or deliverable it drafts, and a chat reply where the reply's own prose is the deliverable, a drafted chapter, an email, a summary. Not the routine back-and-forth of a session.

Never the person's own prose in their own sources, at compile time or in a correction pass. The test is authorship, not location. Status lines and frontmatter are metadata.

**Meaning is not the writer's to change.** A pass may sharpen how something is said. It may not add, remove, soften or strengthen a claim. Where a sentence is wrong because the statement behind it is wrong, or a figure looks wrong, flag it and never correct it.

## The anchors

Eight judgment criteria, each naming a way prose fails so the failure is nameable before the fix is.

- **Clarity.** The reader does not decode. The verdict sits in the sentence carrying it, not assembled from three. A sentence needing a second reading to parse fails Clarity even when every other rule passes it, and the repair is to rewrite it rather than justify it.
- **Hierarchy.** Important looks important. Failure mode: everything is bold, therefore nothing is.
- **Intent.** Every choice is defensible when asked. Nothing reads as the default deciding.
- **Coherence.** Parts agree. Tension only where the sources put it.
- **Restraint.** Compress before adding. Prose only, never apparatus.
- **Generosity.** Linger at the load-bearing moment, where ambiguity would cost the reader. Visible only because restraint is the default.
- **Honesty.** No decoration over absent depth, no hedging over absent view. Cognition's calibrate-never-launder duty is the stricter form.
- **One strong moment.** Exactly one commitment carries the lift, the rest supports. It fails two ways: either nothing commits, or the lift is asserted over a claim already made instead of being earned by it, which is the counterfeit cleft in §3. **Suspended for wiki notes**, see §5.

**Slop and overkill are one refusal.** Slop averages into the plausible default; overkill covers a thin idea with volume. The write-time question is one: is this committed to a source and to one point, or am I averaging into plausibility, or covering a gap with volume?

The anchors derive from the `taste` skill. Where that skill is vendored, the copy is a snapshot to refresh from, never a second statement to consult.

## 1. Before drafting: know the reader

Diagnose the audience, then write for it. Five questions, answered from context and recorded in the deliverable's `[!ai]` callout: who is in the room; what they already know; what they care about; the power dynamic, presenting up, across or down; and the decision context, approval, buy-in, education, inspiration or closing.

Ask when the context does not answer them. Do not guess an audience.

**The diagnosis is re-asked on each pass, never inherited.** A revision that changes what a section rests on can change who it is for. The callout records the date the diagnosis was last actually taken, which is not the date the document was last edited.

**Language.** The wiki is monolingual, in the language recorded in `augment_wiki/config.yaml`: taken from the sources when they agree, asked once when they do not, English by default. Deliverables are written in the reader's language instead.

**Register follows the diagnosis, per topic and not per room.** A room is not one level. A real diagnosis records several in one sentence: expert on their own network and buildings, informed on energy, unfamiliar with embodied carbon. Write each topic at the level the room actually holds it. Never explain back a thing they own, never leave unexplained a term only you use, prefer the plain word where both are exact, and never simplify a term that has no plain equivalent. Writing to the least specialist reader flattens all levels to the lowest, which reads as condescension to most of the room.

Wiki notes need no diagnosis. Their reader is the archive's owner and the next compilation.

## 2. Pass 1, draft

**Read before writing, and read outward.** Open what the document cites, then follow the wiki both ways: the sourced links out of those notes, and the notes linking back. Backlinks are frequently the better path, because a wiki note is compiled from several sources and has already reconciled them. A draft written from the citation list alone will miss it.

**A rewrite is not an edit, and the difference is the drafting order.** Rewriting from the sources means the new text is written before the old text is consulted, then diffed against it to check nothing sourced was lost. Reading the old version first and adjusting it is an edit: it inherits every sentence it does not touch, defects included, and it cannot discover that a sentence stopped matching its sources.

**The sequence is mechanical, and without it the rule cannot be honoured.** Extract the structural brief from the target, close it, draft into a scratch file from the cited sources alone, then open the target and splice. A pass that reads the old prose first has already become an edit, and no amount of intending otherwise converts it back. Two consecutive passes labelled as rewrites have carried over 85 and 80 percent of their sentences byte-identical while each asserted a clean read-back, so the claim is checked rather than trusted:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/rewrite_check.py" <old> <new>
```

Either the carryover number is low or the label is wrong.

**Keep the document in the document.** The body is plain prose at the top level. The `> [!ai]` callout carries only what is about the text: provenance, the audience diagnosis, the governing claim, what changed since the last revision. A deliverable written inside its own callout cannot be read, printed or lifted into a deck without stripping it first.

**Cite in numbered footnotes**, defined at the foot. The list records everything consulted, including notes reached through links and backlinks, not only what is quoted: a reader checking the reasoning needs the path, and a later revision needs to know what ground was covered.

**Ground it.** Every claim traces to a source. Name the quantity, the mechanism, the object, the consequence. Abstraction is where a document stops being checkable.

### Titles

**A title is a retrieval key first.** Prefer the shortest title that is clear and stop there, since a wiki note's title is read in hub listings, link previews and search results, where length costs more than nuance buys.

- **Keep the name.** Where the sources name the thing, that name is the title or its subject.
- **A predicate is allowed, never required.** "The 15-minute city puts services within a walk" earns its verb because the threshold is the model; "Robust typology as circular carrier" does not need one.
- **Entities take a bare name**, optionally with a locating phrase.
- **Procedures take an imperative** naming the task.
- **Ten words is the ceiling, not the target**, and `conformance.py` fails the run above it.
- **The filename never follows the title.** A slug is a link target, and renaming it breaks every inbound link and every `sources:` entry.

A rewritten title is a real cost, since a note is cited by name in conversation and remembered by it. Change one only where it is wrong or unclear, never to bring it into a pattern.

### Mechanical from the start

These carry no claim, so nothing is lost by applying them from the first keystroke.

**Typography.** Flowing paragraphs, never hard-wrapped, line breaks only where structural. No em dashes, no middle dots. En dashes only for ranges and paired asides.

**One governing idea drives the document.** Every section serves it. A section that does not is either supporting a different document or is the finding that the governing idea was wrong.

**Bold marks one claim per section.** Labels and table headers are structure and do not count. In running prose, one bolded phrase per section, on that section's contribution to the governing idea. A bolded claim not serving the governing idea is a hierarchy defect rather than a typography one. Never a word bolded for emphasis, and never a substitute for a sentence that should carry itself.

**Write in the target language, not through it.** Four things carry across between languages and must not.

- **Vocabulary.** Translate domain terms rather than borrowing them, and watch gender and agreement on anything carried across. A term the sources use deliberately is vocabulary, not contamination: keep it and flag it.
- **Sentence architecture.** An apposition chain, a colon reveal or a subject held away from its verb can be native in one language and unreadable in another. Build the sentence in the target language from the claim, not from the shape of its twin.
- **Reference.** Every pronoun, numeral and ordinal must resolve in the target language's own grammar. French `l'une … l'autre` resolves against feminine antecedents that Dutch `het ene … het andere` does not have, so the Dutch sentence is stranded while the French reads cleanly. Name each antecedent before moving on.
- **Metaphor.** A figure living on a pun in one language dies in the other. French `échelle` is both a ladder and a measuring scale, so *elle ne mesure rien* is native; Dutch `ladder` carries only the first, so *de ladder meet niets* is nonsense.

**Sibling versions are written from the sources, never from each other.** A bilingual document is identical in its claims and independent in its phrasing.

**A document's own previous version is a sibling too, and the same rule binds it.** A revision carries no claim, sentence or figure forward: a claim reworded is a claim never re-checked, and the rewording hides that it was not. What may be inherited is bounded and structural, the heading, the section's position and its role in the argument, taken as a brief rather than read as prose. The failure this closes does not look like a failure, since a section reported as rewritten with every content word swapped for a synonym leaves the claim untouched. Synonym cycling is the visible symptom; drafting from the previous version is the cause.

### A table is not prose

A table is a lookup surface, and three rules misfire on it.

**Bold marks the row the comparison turns on**, separate from the section's one prose claim. That is navigation, not emphasis.

**The cell carries the magnitude**, in the unit the reader will check or budget with. The relationship belongs to the prose introducing the table.

**A cell is a fragment, not a sentence.** The portability test does not reach it. "Conforme", "à compléter" and "n.v.t." are identical across projects by design, and that is what makes a column scannable.

## 3. Pass 2, read it back against the sources

Reinforcing and cutting are a single move. A pattern is not deleted and then replaced; it is replaced *by* the claim it stood in front of.

**One motion for a wiki note.** The source-facing checks below are applied as the note is written. The separate pass is reserved for published documents.

### Audit against the anchors

Walk the eight that bind this layer per §5. For each: pass, warn or fail, and the concrete fix. Where two conflict, and Restraint against Generosity is the usual pair, surface the tension and decide it deliberately rather than letting one win silently.

### Against the sources

The target does not move, so these converge on rerun. Everything written gets them.

**Return to the sources, and to the notes around them.** Is every claim still supported as written, and is anything load-bearing still unused? Check the backlinks for material that arrived after the first pass, or a note reconciling two sources the draft treats separately. A draft leaving the strongest available evidence on the table is weaker than its sources allow, and no check on the wording reveals that.

**Replace a rhetorical pattern with the claim it stood in for.** Each usually marks where the writer knew something mattered but had not said what. Write that out with the specifics the sources carry and the pattern goes with it; where it carried nothing, cutting it loses nothing; where the sources carry nothing that fits, stop and ask rather than writing around the gap. Cut on sight: **colon reveals** (a noun phrase, a colon, a dramatic lowercase reveal), **faux-insight setups** ("what most people miss"), **importance puffery** ("marks a pivotal moment"), **profound closing lines**, **summary-recap endings**, **synonym cycling**, **superficial -ing analysis** ("highlighting the team's commitment to"), and **counterfeit clefts**.

**The counterfeit cleft** is a cleft construction whose focused element is a demonstrative pointing back at what was just said: *et c'est ce fait, plus qu'aucun autre, qui décide de*, *precies dat verschil is wat*, *and that is what makes this decisive*. It introduces no term. It restates the previous sentence under an emphasis frame and asserts that the sentence mattered, which is the forged half of the One strong moment anchor.

**The test is the focus, not the construction.** A cleft focusing a new noun carries a real contrast with two full halves and stays: *la consommation des neufs est maîtrisée, et c'est l'impact carbone de la construction elle-même qui devient déterminant* names a new subject and states a shift. A cleft focusing an anaphor points at a term already in play and adds nothing. The demonstrative test works in every language.

This bars neither concluding nor clarifying. A conclusion adding meaning to a section belongs there, written as its own sentence rather than appended: a tacked-on clause inherits the previous sentence's subject and drifts toward restating it, while a standalone sentence has to supply a subject and therefore has to say something. Where the conclusion is already stated elsewhere, the repair is to cut rather than reword.

**A contrast is only a pattern when one half is empty.** "Not just a renovation but a transformation" sets a claim against a strawman. "The shell stays, the services go" names two real subsystems with opposite sourced verdicts. The test: could each half stand as a row in the document's own table?

**Portability test.** Could a sentence move unchanged into another project? Then it is filler: make it specific, or cut it.

**Subject or document?** Does this sentence claim something about the subject, or about the text itself? A line saying the argument is robust, or that a section delivers what it promised, tells the reader nothing.

The practice's own working papers are the same fault one step out. Notes, minutes and visit records are where a judgment was recorded, not an authority licensing it. *Cet ordre est celui de nos propres notes* attributes a professional judgment to a document instead of owning it, and reads to a client as though someone else decided. Three repairs, chosen by what the sentence is doing: a **practice judgment** is stated as the practice's position with the citation clause dropped, since the footnote already carries provenance; a **calibration** moves from container to evidential status, *un constat de visite* rather than *nos notes de visite*; a **client's own statement** is attributed to the client by name, since naming the container hides which party said it.

**Where it hides.** Not spread evenly. It gathers at section openings and closings and at the seam between two claims, wherever a transition feels owed. Read the first and last sentence of every section against this test, plus every sentence naming the artefact.

**Language that slipped.** Domain terms borrowed rather than translated, gender and agreement errors on those borrowings, calques, filler in the target language. Compilation translates, so this bites hardest on notes written from sources in another language.

**Read it as a reader, once, at the end.** One pass whose only question is whether each sentence parses on first reading, asked as someone who reads this language for a living rather than as someone checking rules. A sentence satisfying every rule here and still needing a second pass to parse is a defect, and no rule will find it, because the rules test properties the sentence has rather than the effort it costs.

### The apparatus is not prose

Restraint compresses prose. It never touches footnotes and the consulted list, a placeholder naming a gap, tables and their rows, a SWOT block, a `## Decisions` block, or link contexts and their `Source:` lines.

The reason is mechanical. `verify`, the restyle pass and every later rebuild read that apparatus. A cut footnote does not make a document denser, it makes it uncheckable, and the loss is invisible until someone needs the trace.

### Against the reader

Judgement with no fixed target, so these vary on rerun. Published documents only.

- Does the governing idea survive reading the headings alone?
- Does every section advance it, or does one repeat another?
- Do the figures carry a relationship the reader retains, rather than a magnitude?
- **Is the honest weakness worth stating here?** A professional reader discounts an argument conceding no risk, so where the governing idea rests on an assumption that could fail, naming it and saying what would settle it makes the document stronger. Not owed by every deliverable: a manufactured caveat is filler and fails the portability test.
- **Does the finished document still answer its diagnosis?** A draft that drifted from its reader is caught here or not at all.

## 4. Release check

The gate a published document passes before it is emitted. Mostly not a model pass.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/release_check.py" <file>
```

Scripted: every footnote defined and used, wikilinks resolving, typography swept. Run it, read the output, fix what it names.

By hand, because a script cannot: grammar and consistency, each language by its own conventions, quotation marks, spacing around punctuation, one convention per document for numbers, units and dates, acronyms expanded once. This needs the whole document, which is why it waits until there is one.

## 5. When the passes and anchors run

The line is not the vault's edge. It is whether the vault regenerates the text.

**Wiki notes: one pass.** §2's drafting rules and §3's source-facing checks in a single motion. No separate read-back, no reader-facing half, no release check, no audience diagnosis. They are compiled from sources, rebuilt whenever those change, and corrected by fixing the source and recompiling, so a surviving defect is swept on the next cycle rather than needing a gate.

| Anchor | Wiki note | Published document |
|---|---|---|
| Clarity, Intent, Coherence | bind | bind |
| Hierarchy | structural only: the single claim is findable | binds fully |
| Restraint | binds, prose only | binds, prose only |
| Generosity | completeness of what the sources carry | lingering where the reader would stumble |
| Honesty | binds; calibration is its stricter form | binds |
| **One strong moment** | **suspended** | binds |

**One strong moment is suspended for a wiki note** because cognition requires each position at its honest weight. A note engineered so one commitment carries the lift has added emphasis its sources did not carry, and §0 bars strengthening a claim. The reader-facing half of §3 is excluded for the same reason from the other direction: strengthening against a reader has no fixed target, so it varies between runs and a note would drift without its sources changing, which is instability rather than improvement.

**Published documents: two passes and a script.** Anything the vault does not regenerate gets the diagnosis, pass 1, pass 2 in full including the reader-facing half, all eight anchors, then the release check. Assisted source notes count even though they never leave the vault, since nothing rebuilds them and a defect in one is permanent.

`conformance.py` enforces the deterministic typography rules with no model call, on every layer. It reaches punctuation and artefact self-reference, never a colon reveal or a faux-insight opener.

A correction pass on existing text reports three things: the corrected text, what changed by category as "was → is", and what was flagged and left alone.
