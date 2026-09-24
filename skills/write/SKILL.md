---
name: write
description: Write into the source layer, the person's own authoritative notes. Use to capture or store something, note this down, file a memo, attach a comment or caveat to an existing source, or record that a wiki note is wrong. Covers capture, comment and correction, which are three shapes of the same act and share one set of hard rules. Never writes a wiki note.
---

# Write

**Everything the system writes into the person's own layer comes through here, and none of it ever touches prose they wrote.** The wiki is compiled output, so a correction or an observation written there is destroyed by the next build and lives only in a derived file nobody treats as authoritative. Routing it to the source preserves it, attributes it, and improves every future compilation rather than one paragraph.

Read `rules/freshness.md` and run the check first. Read `rules/write-flow.md` as duties before drafting any prose, since this skill writes into a layer whose existing text must never be touched.

## Which mode

| The situation | Mode |
|---|---|
| Material worth keeping that has no source note yet | **capture** |
| A source is not wrong but incomplete: a caveat, a scope boundary, a cross-reference, a question | **comment** |
| A wiki note is wrong, and the fault is in the synthesis | **correct** |
| A wiki note is wrong, and the fault is in the source | Neither. The person edits their own source; the changed hash re-queues it. |

## Hard rules, all three modes

**Append, never edit.** The person's prose in their own sources is untouchable, at capture time, in a comment and in a correction pass alike. The test is authorship, not location.

**Set the declaration, and nothing else of the system's.** `augment:` carries the state tag, with `created:` written once at first write and `updated:` on every later edit, both read from the clock rather than typed. The person's own frontmatter fields are read, never written or reordered.

**A status write stays inside the frontmatter.** Never a read-and-rewrite of the whole file, which can silently normalise the body's line endings, change the content hash and re-stale everything compiled from that source. The block itself is outside the hash, so giving a bare-form file a fenced block is safe.

**Identify every addition at the moment it is written.** `assisted_by:` in frontmatter as `<producer>/<version>`, read from the runtime, never a bare product name and never copied from an example. Model-written prose sits in a `> [!ai]` callout; the person's own transcribed words sit in `> [!note]`. Neither is ever mistaken for the other, because the next compilation calibrates them differently.

**Default to `#to-process`.** Use `#excluded` when the person says so, or when the material is client-confidential and they have not said to process it, and ask rather than assume.

## Capture

**1. The destination decides whether processing follows.** Where the person names a home in the source tree, write there, and the note is in scope and ready. Otherwise write to `_inbox/`, which is the default: inbox notes are unaddressed and out of scope until the person assigns them an address. **Never invent an address**, and never infer one from the session's topic.

**2. Write the frontmatter,** the three system keys and nothing else, plus `assisted_by:` where the model drafted any prose.

**3. Record the citekey** for an external source, with the full reference at the foot of the note.

**Be selective.** At the end of substantial work, offer to capture what was established, not a transcript of it. Most sessions are scaffolding rather than source material, and an over-full tree exhausts its addresses fast. If it will not be returned to, do not file it.

## Comment

**Never on its own initiative.** A comment is written only when the person asks for it, or validates it at the sweep. No cycle comments, and no operation adds one because it noticed something. A finding surfaces as an offer; the comment follows the person saying yes. Writing into a source is the one thing the system does to the person's own layer, so it stays under explicit human control, and an unprompted comment is a violation rather than a convenience.

**1. Confirm the target is a source, and in scope.** Never a wiki note, which is compiled and would wipe it. Never an `#excluded` or undeclared source. If the source states something false, this is `correct` instead.

**2. Choose the callout by authorship, then place it at the front.**

The model's own observation, a judgment, caveat, cross-reference or discussion finding:

```markdown
> [!ai] augment/claude-code, 2026-07-25
> The observation in plain prose, one flowing paragraph on one line, marking anything
> drawn from outside the vault as such so the next compilation can calibrate it.
```

The person's own words, dictated and transcribed rather than composed:

```markdown
> [!note] mdh, 2026-08-21
> Their words as given, not paraphrased or reworded.
```

The actor for a `[!note]` is read from `author:` in `augment_wiki/config.yaml` at write time, never hardcoded. **If that key is absent, ask for the name, write it to the config, then proceed.** Never fall back to `[!ai]` for want of the key: a dictated sentence marked `[!ai]` is a false provenance claim that understates its own weight at the next compilation.

A general comment goes at the top of the body after the `# Title` line; a comment on one section goes at the head of that section after its `## heading`. Before the material it qualifies, never after it, and never woven into the prose.

Keep the callout on one line. A paragraph wrapped across several `> ` lines reads as damaged in Obsidian.

**3. The hash drifts, and that is the point.** A callout is body content rather than an excluded metadata line, so the stored hash no longer matches. Mark the wiki notes compiled from this source `#stale` now, with a byte-preserving write, so the queue shows the rebuild immediately rather than waiting for the nightly detect.

**4. Log it in history:** the source id, the date, and the notes it re-stales. Append-only.

**5. Leave the rebuild to the nightly cycle.** It detects the hash drift as it does for any changed source and recompiles from the source including the comment. Rebuild by hand only on explicit ask.

**A comment that narrows a claim also puts the note's edges in question.** The rebuild re-derives the note's sourced links rather than carrying them across, and re-scores its keyword edges. Where the observation is that a claim reached less far than the wiki thinks, say so in the callout, since that is what the rebuild reads.

## Correct

A correction is itself a source, and it outranks what it corrects.

**1. Establish what is wrong**, and whether the error sits in the source or in the synthesis. An error in the source is the person's to edit; the changed hash re-queues it and nothing further is owed here.

**2. Write a correction note** into the source tree, `kind: correction`, answering three questions in order: what the process concluded, what is actually the case, and on what basis. This is the person's knowledge and worth keeping regardless of the wiki.

**3. Tag it `#to-process`** and cite the wiki note it corrects.

**4. Mark the affected wiki notes `#flagged`.**

**5. Log the flag:** the note, the date, and whether the fault was source or synthesis. This is the system's primary quality signal, and the sweep reads it as a rate.

**Be a partner, not a mirror.** If the correction rests on a misreading of what the sources actually say, say so rather than agreeing.

## Never

- Edit, rephrase, reorder or delete the person's existing prose in a source.
- Edit a wiki note in response to any of this.
- Alter a source to make the wiki come out differently.
- Add a comment unprompted, or use one to smuggle a correction. A false source is a correction, which outranks; a comment only adds.
- Write an unmarked passage into a source, or mark the person's dictated words `[!ai]`.
- Present an outside-the-vault claim as if the source established it.
- Assign an address in the source tree. The person does that.
- Discard a flag once the reprocess is done. The log is the metric.
