# Getting started

## Pointing it at an archive you already have

This is the normal case, and the one the system is shaped around. You have a few hundred or a few thousand notes in some scheme of your own, and nothing has been declared.

**Nothing is processed until you say so.** Run `/augment:dream` once and it reports how many sources await declaration rather than sweeping them in. In an archive holding client or confidential work, deciding on your behalf is the dangerous error, so the first run's output is a question rather than a wiki.

Then run `/augment:verify` and answer two things in order. First the folders: each top-level folder no rule touches is put to you with its file count, and you answer in scope with a default or out of scope. Either answer takes it off the list permanently, and a folder nobody has ruled on stays visibly undecided rather than being quietly treated as excluded. Second, within the folders now in scope, the sources carrying no status, declared in bulk by folder rather than note by note.

**Start with the folder you know best.** The first batch is what tells you whether the output is worth continuing, and you can only judge that against material you remember. Roughly half the notes surviving without correction is the rough threshold; well below it, narrow the scope rather than processing the rest.

## Starting from nothing

If the vault holds no source folders at all, the sweep asks where your notes should live and records the answer rather than creating a tree on a guess. A structure guessed at setup is the hardest of all to undo, because everything filed afterwards inherits it.

## The shape of a week

Most days you do not invoke anything directly. You write notes where you always write them, and ask the archive things in passing.

The **cycle** runs nightly, scheduled or on demand. It detects what changed, rebuilds what went stale, consolidates new material, runs the checks, anchors and connects the notes it wrote, regenerates the views and reports to a queue.

The **sweep** runs weekly and is the only part needing you. It should take about fifteen minutes. You read the list of what the cycle wrote unattended and say if anything is wrong, then answer the decisions the cycle is barred from taking alone: what to remove, what to split, what to supersede, what to contest, and anything touching your own notes.

Everything else is reading and asking. `/augment:answer` retrieves or synthesises, `/augment:discuss` argues back.

## What you never do

**You never edit a wiki note.** It is compiled output and the next build overwrites it. If a note is wrong, `/augment:write` files a correction as a source, which outranks what it corrects and improves every future compilation rather than one paragraph. If a source is merely incomplete, the same skill attaches a marked comment to it in place.

**You never lose an edit you made in your own notes.** The system writes into a source's frontmatter and nothing else, and never touches a word you wrote. Two lines are its own: `augment:`, the source's status, and on a source the wiki cites, `wiki:` directly under it, listing the notes that cite it, so you can follow a source to what was made of it without leaving your editor. Neither line counts toward the content hash, so neither ever makes the wiki rebuild.

## First-run checklist

1. Install the plugin, and confirm `/augment:wiki` responds.
2. Create `augment_wiki/config.yaml` with at least `house_language` and `author`.
3. Run `/augment:dream`, and read the census rather than acting on it.
4. Run `/augment:verify`, and declare folders starting with the one you know best.
5. Run `/augment:dream` again to consolidate the first batch.
6. Read the notes it produced against sources you remember, and decide whether to widen the scope.
7. Once you trust the output, set up the nightly routine, per `scheduling.md`.
