# Provenance: assistance, not co-authorship

## Runtime values are read, never typed

Two values in this system have an authoritative source outside the writer's head: **the clock** and **the runtime id**. Both are obtained at write time, from that source, for every field carrying them: a source's `updated:`, a callout's date, the index's `compiled`, `processed`, `declared` and `ran`, a changelog date heading, and a version stamp.

Typing either from memory or inference is the same defect wearing two costumes. **A date typed from inference drifts, and drifts in one direction**, since successive edits in one session bump it like a version number and put the record days ahead of the work. A model id typed from an example goes stale the moment the model changes, and is then a false statement about who did the work. Conformance fails the run on any metadata date later than today, which is the mechanical half of this rule; only metadata is checked, since prose legitimately cites future years.

## Source notes

Some are written with assistance:

```yaml
assisted_by: augment/claude-code
```

The value follows the OKF actor convention, `<producer>/<version>`: the producer is the agent that did the work, `augment` rather than whatever harness it ran under, and the version names the **runtime**, not the model. **Read it from the runtime; never copy it from this example.**

Naming the runtime rather than the model is deliberate. A session can change model midway, so a model value would be wrong for half the writes it stamps, and it is the agent plus its runtime that determines how the work was done. A literal model id baked into a reference file is copied forward by every session that reads it and is wrong the moment the model changes.

One value, no free text. What the assistance actually was, drafted the SWOT, proposed the structure, belongs in the callout below, where a reader looks for it. Keeping the field to a bare identifier is what makes it groupable and greppable across the archive, which hand-written phrasings are not.

OKF also defines `human:<id>` and `process:<id>`. **Neither is adopted.** A vault has one author, and the field is omitted entirely when absent, so a note with no field is the person's own by construction. Never write `assisted_by: none`.

Deliberately the same word as the git `Assisted-by:` trailer, one vocabulary across prose and version control. **Never `Co-authored-by:`**, because the person is the sole author and the trailer must not claim otherwise. This matters once the cycle runs unattended, since such a run commits under the person's own identity and the trailer is then the only thing distinguishing an overnight machine pass from work done by hand.

The convention applies to new writes. Notes carrying an older free-text form are not rewritten to it: they are provenance records, and a note migrates when it is next touched. Where a past note records assistance but not which runtime, that gap stays a gap, since inventing a version to satisfy the format would be fabricating provenance.

## Marked passages inside a source

Model-written prose:

```markdown
> [!ai] augment/claude-code, 2026-07-18
> Passage drafted with assistance.
```

The callout carries the **same actor value** as the frontmatter field, followed by the date. One vocabulary across the field, the callout and the git trailer means a reader learns the form once. A callout naming a bare product records less than the field directly above it, which is the gap this closes.

**A `[!note]` callout marks the opposite case**, the person's own words, dictated in conversation and transcribed rather than composed:

```markdown
> [!note] mdh, 2026-08-21
> The person's own words, transcribed as given.
```

The type differs because the distinction is load-bearing downstream: an assisted passage is calibrated as a **weaker** input than the person's primary text, so marking their own dictated words `[!ai]` would instruct the next compilation to discount them, a false provenance claim pointing the wrong way. The actor is the person's own name or initials, read from `author:` in `config.yaml` and never hardcoded, so the system stays usable on any vault. If the key is absent when it is needed, ask for the name and write it to the config before proceeding; never fall back to `[!ai]` for want of the key.

Unlike the status line, which is metadata and hash-neutral, **a callout is body content and shifts the content hash**. This is by design: it is the mechanism by which a comment induces reprocessing, since the next cycle detects the changed input and rebuilds every note compiled from that source, now reading the comment.

## Wiki notes

Wiki notes carry no `[!ai]` callout, because the whole layer is model-written and marking passages inside it would say nothing. They carry `generated.by` instead:

```yaml
generated:
  by: augment/claude-code
```

Same actor convention, so one vocabulary covers both layers. Two things earn it its place. A wiki note carries its own citation list, which makes it a self-describing document, and a self-describing document omitting who wrote it is only half-describing. And **the layer has more than one producer**: a concept note is compiled by the model, while a hub, a view or a theme body is emitted by a deterministic script and names that script. Saying the model wrote a generated index would be a false statement about who did the work, the same defect as a stale model id.

`human:` and `process:` stay unadopted here too. This field records a producer, and the producers are the agent and its scripts. There is no case in which the person is one, because the person does not write wiki notes.
