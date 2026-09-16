---
name: answer
description: Retrieve from the vault and answer from it. Use when the person asks to find or search notes, which notes cover something, to show them what exists, what the archive knows about a topic, or to be briefed on something. Returns either the notes themselves or a synthesised prose answer with citations and a statement of what the vault does not know. Read-only, and the correct default when a request is ambiguous.
---

# Answer

Two modes over one retrieval. **Retrieve returns notes; synthesise returns an answer.** Ask which is wanted only when the request genuinely does not say; a request for "notes on X" wants the first, "what do we know about X" the second.

Read `rules/freshness.md` and run the check before retrieving. A clone behind the vault returns results that read current: notes since changed, notes since added simply absent from the set. An answer is the failure with no downstream catch, since it leaves cited and the person acts on it.

## Duties in force

- **Nothing unsourced.** In retrieve mode the results are notes, not paraphrases of notes. In synthesise mode every claim traces to a note and through it to a source, or is marked as coming from outside the vault.
- **Calibrate, never launder confidence.** Stale or flagged inputs make an unreliable answer, so say so and state the confidence with its basis.
- **Multi-sided; steelman the under-challenged.** Surface the tensions the vault holds, and where a bearing position is under-argued add its strongest counter at honest weight. Do not pick a side for the person.
- **SWOT the forward-looking.** Where the question is forward-looking or fast-moving, close with a labelled SWOT: genuine upside and its conditions against the obstacles, scenario-based and never manufactured.
- **Inform, do not obstruct.** This operation stays frictionless. The effortful challenge belongs to `discuss`, which the person opts into.

## Retrieval

**1. Read the index first.** `augment_wiki/index.jsonl` is one file carrying the title, type, status and sources of every note. Narrow there before opening anything: by type where the request implies one, by source where it concerns a known project, by title match, by status where currency matters.

**2. Open only what survives the narrowing.** The index says what exists and where; the notes say what they hold. Reading the whole vault to answer a narrow question is what the index exists to prevent.

**3. Match the depth to the question, and descend into the sources for detail.** The wiki is a point of entry into the sources, not a wall around them. A general question is usually answered from the notes. A detailed one is not: it needs the sources those notes cite, and the other sources in the same context, **including the processed-but-unlinked ones**, meeting notes and how-to files that no concept was extracted from but that still hold the specifics. Reach them through the `sources` view, which lists every source under its project or library context and marks the unlinked ones. An absent wiki note means unprocessed material, not absent material, and the index shows whether the relevant sources are still `#to-process`.

## Retrieve mode

Return each hit with its build state visible, so a `#current` note and a `#stale` or `#flagged` one do not look alike. Surface the underlying source alongside the wiki note, since the source is what the person actually wrote and is usually what they want.

Report honestly when the vault holds little or nothing. An empty result is information; a padded one is noise.

## Synthesise mode

Compose the actual answer in prose, not a list of chunks.

Cite every claim to its note, and prefer the underlying source where the distinction matters. **Keep the two layers distinct in the citation:** a claim carried by a wiki note is cited to the note, while a specific read straight from a source that no note yet carries is cited to the source and marked as such, so the reader can tell derived synthesis from raw source. Blurring them is what makes the closing statement untrustworthy.

**Close with what the vault does not know.** This is the point of the mode; without it this is a search engine with better prose. Cover, where each applies: supporting notes that are `#stale` or `#flagged`; sources materially older than the topic's rate of change; any `#contested` tension bearing on the question; what is simply absent; and the channels the vault cannot see, email, drawings, meetings, site.

```
Hemp and wood-fibre insulation buffer moisture as well as heat, which is what
makes the thermal argument hold in timber frame
[[bio-based-insulation-moisture-buffering]]. The standard detail assumes a
non-buffering cavity [[vapour-barrier-standard-detail]].

**Gaps:** the first note is `#stale`, its links now citing four sources its body
was never compiled from. The TOTEM figures date from 2024 and TOTEM has
published since. Nothing covers acoustic performance, and the two notes are
linked `contradicts`: see `!tension-vapour-control-in-buffering-assemblies`.
```

## Never

- Fill a gap with general knowledge presented as vault knowledge. If it comes from outside, say so in the same sentence.
- Omit the closing gap statement because the answer looks complete. Looking complete is exactly when the omission does damage.
- Write anything. This skill reads. Something that came out wrong goes to `write`; thinking it through goes to `discuss`.
