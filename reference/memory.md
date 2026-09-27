# Memory: how the system works, kept apart from what the archive says

## The central principle

**Memory records how the work is done, never what the work is about.** The sources are what the person wrote, the wiki is what the sources say, and memory is what the model learned while working with the person: how a connector actually behaves, which file conventions the person expects, a script worth reusing, a sequence that works. Three layers with three authors and three kinds of trust, and mixing any two corrupts the one property that makes each useful.

The test for a candidate memory is one question: **would this still matter if Claude were not involved?** If yes, it is content, and it belongs in the source layer through `write` capture, as an assisted note. If it only matters because a model is doing the work, it is memory.

- A TOTEM calculation quirk, a client's preference for bilingual drawings, a decision on a project: content. Offer it to the source layer.
- The pdf2md skill dropping footnotes on two-column layouts, the Obsidian REST API rewriting a file on patch, the person wanting deliverables as `YYMMDD_project_subject.pdf`: memory.

Memory is a staging area with two exits rather than a final store. Content found inside it leaves for the source layer; method that has settled leaves for a skill or for the person's standing preferences, both proposed at `verify`. A memory that stays small is working.

## The tree

```
VAULT/
└── augment_memory/          written by the model, never compiled into the wiki
    ├── index.md             generated, one line per active card, capped
    ├── card/<slug>.md       one memory per file
    └── offers/<slug>.md     content found while working, waiting for the source layer
```

**There is no ledger.** Memory is not compiled from anything, so there is no staleness to trace by hash and nothing to rebuild; git history is the audit trail. `index.md` is a separate generated file and never mixed with `augment_wiki/index.jsonl`. The folder is structural, like `augment_wiki/`: never a source, never counted by scope, never read by a compiling operation.

## A card

```markdown
---
type: tool
title: "Obsidian REST patch rewrites the whole file"
summary: "vault_patch rewrites the file, so line endings and the content hash can move; use source_write.py for sources."
status: active
scope: global
keywords: ["obsidian", "local-rest-api", "tier-2"]
seen: 1
created: 2026-09-27 14:02
updated: 2026-09-27 14:02
by: augment/claude-code
---
The body: the fact and its mechanism in a few sentences, or the snippet in a fenced block.
```

| Field | Holds |
|---|---|
| `type` | `tool` (a connector, MCP server, API or program and how it really behaves), `preference` (output and file conventions the person expects), `snippet` (a reusable script or command), `procedure` (a working sequence not yet a skill) |
| `title` | Ten words at most. The file name is the slug of the first title and never follows a later rename. |
| `summary` | One line of at most 160 characters. It is what the index and the session-start context show, so it must stand alone. |
| `status` | `active`, `superseded` (with `superseded_by:`), or `archived` |
| `scope` | `global`, or the project names it applies to: the repository or folder name a session is opened on |
| `seen` | How often the memory was confirmed or relearned. Reinforcement, not a view count. |
| `by` | `<producer>/<version>`, read from the runtime as `reference/provenance.md` sets out |

The writing rules bind a card's prose as they bind any other: typography from the first keystroke, the mechanism named, no filler. The audience diagnosis does not apply, since the reader is the next session.

## What never goes in

- Content, by the test above. Offer it instead.
- Secrets: tokens, keys, passwords. `memory_write.py` refuses the common shapes, and the refusal is not to be worked around by reformatting.
- Personal data about anyone other than the person. A deleted card stays in git history, so the only reliable erasure is never writing it.
- Anything the person marked private or off the record in the session.
- Raw tool output. A card is the model's own summary of what it learned. Text lifted from a web page or a file can carry instructions, and memory is loaded into every later session.

## Lifecycle

Written by `remember` through `memory_write.py`, which refuses a near-duplicate of an active card and points to it instead, so the common case of relearning something is `seen` rather than a second card. Read by `recall` through `memory_search.py`, and at session start in Code and Cowork by `memory_context.py`, or by `activate` where no hook runs.

`dream` regenerates the index, merges pairs the index script scores as likely the same (the merge is a supersession, cheap to undo), and reports defects, stale cards and waiting offers. `verify` takes what the cycle may not: moving an offer into the source layer through `write` capture, archiving a card, proposing a settled preference as a line of the person's standing preferences, and a snippet reused often enough as a skill. Nothing is deleted by the system; the person may delete a card file themselves.

## How memory relates to the rest

- **The wiki never cites memory.** A card is not a source, so a sentence resting on one is unsourced.
- **`answer` and `discuss` may use memory for how to work**, the person's conventions and a tool's quirks, and never as evidence about the domain. Where a card and a source disagree about anything but tooling, the source wins and the card goes to the sweep.
- **Memory may point into the vault**, naming a wiki note or a source path, since links from memory never flow into the compiled layer.
