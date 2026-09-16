---
name: wiki
description: Entry point and router for an intelligence-augmentation vault, a person-authored source tree plus a model-compiled wiki of concept, entity, theme, hub and tension notes. Use when the request concerns the vault or the wiki as a whole, when it is ambiguous which operation applies, or when the person mentions a memo, a source note, a concept or entity note, the backlog, the nightly cycle, the sweep, digesting, flagging, or asks what the archive knows about something. Routes to write, process, answer, discuss, mint, dream and verify.
---

# The vault

**The wiki is derived. The person writes the sources; the model writes and maintains every wiki note.** Summarising, cross-referencing, filing, detecting contradictions and drift, compiling and recompiling are the model's. Choosing what to read, what to capture and which questions are worth asking are the person's.

The person does not edit wiki notes. Corrections travel through the sources, never through the derived layer. Any operation that increases the person's tool-management burden is misdesigned.

## Before anything

**Run the freshness check first, on every operation, including read-only ones.**

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_freshness.py" <vault> 
```

Pull if it reports behind. A vault syncs from several directions at once (the owner's editor, mobile sync, the nightly cycle, another session), so a working copy goes stale while a session is still inside it. A stale write is caught by the push and the next cycle; a stale read is quietly delivered as a cited answer the person then acts on. Pulling once at the start settles nothing about the turn you are in.

**Find the vault by its marker, never by inference.** A vault is a directory containing `augment_wiki/config.yaml`. If none is present, say so and stop. Do not create one, do not adopt a structure the person has not named, and do not read `STUDIO.md`, `PROJECT.md` or any other plugin's marker as evidence of one.

## Routing

| The person wants | Skill |
|---|---|
| to capture something, note this, comment on a source, or say a note is wrong | `write` |
| to digest new sources, or `#to-process` material exists | `process` |
| to find notes, or to be briefed on what the archive knows | `answer` |
| to think something through, be challenged, or work a `#contested` note | `discuss` |
| a specific missing concept or entity generated and wired in | `mint` |
| the nightly cycle, the backlog, or what needs attention | `dream` |
| the weekly sweep | `verify` |

Ambiguous requests default to `answer`, which is read-only and cannot damage anything. Ask only when the answer would change what gets written.

Each skill loads the rules and reference fragments it needs and nothing else. Do not read the full reference set before routing.

## Hard rules

These bind every skill and are restated in each. They exist because breaking one is not recoverable by the next cycle.

**Never write prose into a source note.** Sources are the person's authorship. The `augment:` declaration line and frontmatter may be set; the body may not, and a status write is a byte-preserving line insert, never a read-and-rewrite that could normalise line endings.

**Never write an unsourced sentence into the wiki.** Body text and link context alike, everything cites a source.

**Never let a person's edit inside a wiki note stand as authoritative.** The wiki is compiled and will overwrite it.

**Never process an `#excluded` source.** No exceptions and no reasoning around it.

**Never delete.** Supersede in place and link the replacement. Removing an unsourced `keywords` tag is the single exception, and it is the person's decision at `verify`, never a cycle's.

**Never rewrite the index without appending to history first.** History is what makes the index recoverable.

**Never write outside the vault, and never interpret silence as assent.**

## Working agreements

Commit and push to the vault's default branch, but only when the operation actually wrote something. A read-only operation and a run that changed no tracked file neither commit nor push. Check `git status` first; if it is clean, stop.

New source notes default to `_inbox/` unless the person names a home in the source tree. An inbox note is unaddressed and out of scope until they assign it one.

Scripts under `${CLAUDE_PLUGIN_ROOT}/scripts/` are deterministic and are run, never read into context. Reading or reimplementing one wastes tokens and reintroduces the bug it was written to fix. Read a script only to debug the script itself.

Where a reply's own prose is the deliverable, a drafted chapter, email or summary, the writing rules in `rules/write-flow.md` bind it exactly as they bind a wiki note.
