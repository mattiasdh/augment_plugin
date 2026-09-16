# Scope, the ledger, and rebuilding

## The two files

The bookkeeping is split in two, and the split is what makes it safe to rely on.

**`history.jsonl` is append-only and never rewritten.** Every entry ever written goes here first, in the order it happened. Appending is cheap and survives an interrupted run, because a partial append loses at most the line being written.

**`index.jsonl` holds only current entries**, exactly one per id, and is rewritten by compaction rather than appended to. It is written atomically, to a temporary file that then replaces the old one, so a crash leaves either the old index or the new one and never a half-written file.

Because every write reaches history first, **the index is fully derivable**: replaying the history and keeping the last entry per id reconstructs it. A corrupt or missing index is a recoverable inconvenience rather than a loss, and rebuilding it needs no model call.

History also carries **run markers**, one per cycle, with a kind ending `_run`. Each marker's id is `<op>-run-<date>`, suffixed `-2`, `-3` and so on when the same day already carries a run of that operation, so two cycles in one day stay distinct rather than colliding. They are not index entries: compaction skips them, so the index holds notes and sources and nothing else.

**An id whose latest entry carries `retired: true` is dropped from the index at the next compaction.** This is not a deletion and does not bend the never-delete rule: every line that id ever had stays in history, and only the current-state projection stops carrying it, which is precisely the division the two files exist for. It is for **tooling state that has finished**, never for anything that makes a statement.

## What the index carries

It serves two purposes at once, and both shape what it holds. It is **build state**, recording what was compiled from what, so staleness is detected without opening a note. It is also the **first stop for retrieval**, narrowing by type, status or source before any note is opened, because a scan of one file is far cheaper than a scan of the vault and degrades gracefully as the wiki grows.

A source `id` is the full vault-relative path, not the bare basename, because real archives have basename collisions. Wikilink resolution, by basename, and index identity, by path, are deliberately different keys.

```jsonl
{"id":"notes/12.04 selection-criteria.md","kind":"reference","hash":"a3f9c1","status":"processed","processed":"2026-07-21","produced":["augment_wiki/concept/selectieleidraad-vs-bestek.md"]}
{"id":"augment_wiki/concept/selectieleidraad-vs-bestek.md","type":"concept","kind":"model","title":"Selection guide and specification serve different purposes","status":"#current","compiled":"2026-07-21","compiled_from":[{"source":"notes/12.04 selection-criteria.md","hash":"a3f9c1"}],"flags":0}
```

A wiki entry's `type` equals the subfolder it sits in, so a mismatch is visible from the index alone. Its `kind`, `title` and `status` are duplicated from the note so the hubs can be rebuilt from the index without opening every note. **That duplication is deliberate and bounded**: all three are written at compile time from the note itself and checked by the index-divergence pass, so a desync is detected rather than silently tolerated.

**Links are not duplicated into the index.** They live once, in each note's links block. Copying them would create a second version able to disagree with the first, and traversing a handful of files is cheap enough not to be worth that risk.

## The declarations

**The settings the person declares live in `config.yaml`, not in the index.** It is the only hand-written file in the wiki folder: nothing regenerates or reorders it, and it is edited directly. The index is machine state projected from the ledger and is never hand-edited; a declaration is the opposite of both.

```yaml
contract_version: "2026.9.16"   # the plugin release this vault was last compiled under
house_language: en              # ISO 639-1; the wiki is monolingual
author: mdh                     # for the [!note] callout actor

source_contexts:                # how the sources view groups the source layer
  - path: "notes/10-19 Practice"
    group_by: child

scope:
  ignore:                       # never sources: scratch, staging, infrastructure
    - notes/_inbox
    - README.md
  rules:
    - path: "notes/10-19 Practice"
      in_scope: true
      default: "#to-process"
    - path: "notes/30-39 Technical/34 Confidential"
      in_scope: true
      default: "#excluded"
    - path: "notes/20-29 Clients"
      in_scope: false

harvest:                        # narrower than #to-process: dated decisions only
  mode: decision-harvest
  paths: ["notes/10-19 Practice/12 tender"]
```

`contract_version` records which plugin release last compiled this vault. Where it does not match the installed plugin, the cycle reports a migration notice rather than compiling on, since a vault compiled under one set of rules and maintained under another drifts in ways no check downstream can see.

The house language is derived once: a vault whose sources are monolingual takes that language, a mixed archive is asked, an unanswered one gets `en`. Changing it later means recompiling the wiki.

## Precedence and the four folder states

**Precedence is longest path first, and an explicit tag on a note always wins.** In order: a status tag on the note itself, then the deepest folder rule matching its path, then any shallower rule, then nothing. A folder in scope with no default leaves its notes undeclared. **Silence fails closed**, and so does a missing or empty config, which reads as no rules and therefore no folder in scope.

| State | Written as | Meaning |
|---|---|---|
| in scope | a rule with `in_scope: true` | processed under its default |
| ruled out | a rule with `in_scope: false` | considered, and the answer was no |
| **undecided** | no rule touches the path | nobody has been asked yet |
| ignored | listed under `scope.ignore` | never knowledge: scratch, staging, infrastructure |

**Undecided is not out of scope by another name.** It is reported as a decision owed, once, at the sweep, and answering it either way takes it off the list permanently. Without the distinction a folder added this morning reads exactly like one passed over for six months, so the question is never put and the explicit exclusion never gets used. A rule anywhere inside a folder counts as having engaged with it, so a partly-declared tree does not keep asking about itself.

`scope.ignore` is a different kind of thing: those paths are not knowledge and are never counted, asked about, or read. It is configuration rather than a hard-coded list, because which folders are scratch is a property of a vault rather than of the system. The wiki folder itself and any dotfolder are excluded structurally and need no rule.

**Subfolders may include or exclude against their parent**, which is the point: a technical folder can be processed wholesale while one confidential subfolder inside it is permanently excluded, without tagging a single note by hand.

A folder default does not weaken the rule that absence of a decision is not a decision. The decision was still made explicitly, once, for the folder. What it removes is the need to restate it for every note that lands there afterwards.

## Hashing

Each entry in `compiled_from` pairs a source id with the hash that source had at compile time, so staleness is a direct comparison against the source's current hash and needs nothing else.

**The hash covers content, not the whole file.** Five lines are excluded before hashing: `augment:`, `created:`, `updated:` and `assisted_by:`, plus `Status:`, the pre-frontmatter form of the declaration, kept so a stray old-style file still hashes the same. Everything else is content that a process depends on.

The reason is that **declaring a source is not editing it**. Tagging an already-processed source, or adding a status tag to one that never had one, changes no words. If the hash covered the whole file, that keystroke would mark every note compiled from that source stale and rebuild all of them for nothing.

**Content is hashed byte for byte.** Everything outside the excluded lines counts, including line endings and trailing whitespace, so normalising CRLF to LF or reflowing a paragraph changes the hash exactly as editing a word would. **Any write that adds or changes a declaration line must therefore be byte-preserving**, a line inserted without disturbing the rest, never a read-and-rewrite of the kind a text-mode tool performs by default, which can silently convert line endings and is both a content modification of the person's note and a spurious staleness trigger for everything compiled from it.

**The canonical implementation is pinned** at `scripts/hash_source.py`, and is equivalent to `grep -vE '^(Status|augment|created|updated|assisted_by):' FILE | sha256sum | cut -c1-8`. A convenience reimplementation is a trap: Python's `str.splitlines`, for one, also breaks on a bare carriage return and several Unicode separators, so it disagrees on many real files and reports staleness that is not there. Use the shipped hasher.

For the same reason, **a status change does not bump `updated:`**. That field records when the person last changed what the note says, and a declaration says nothing.

Filesystem modification time is not used anywhere. It changes whenever a file is written, survives no copy or clone, and is not tracked by git, so it cannot answer the only question that matters, which is whether the content differs from what was compiled.

## What the index cannot tell you

Everything above answers one question: which notes are stale **inside this working copy**. No part of it answers the other one. The index can be perfectly consistent, conformance clean and drift zero while the whole clone is days behind the vault, because every hash it compares was written by the same stale checkout. `rules/freshness.md` carries that duty.

## Rebuilding

The index is a dependency graph. Each wiki note records the sources it was compiled from, with their hashes, so **rebuild is triggered by input change in the manner of a build system**, not discovered later by scanning.

**Concept notes rebuild on any input change.** A cited source was edited, so its hash differs, or a newly processed source contributes to the same concept. Both are the same event: the input set changed. The note is marked stale at the moment this is detected and rebuilt on the same or the next pass.

**Hub notes accrete.** Every new source in a topic touches its hub, so rebuilding each time would be wasteful. A hub carries an unincorporated count in the index, incremented each time a source is added to its links without its body being rebuilt, and is rebuilt when that count reaches ten or quarterly, whichever comes first.

Rebuilding recompiles the body from the union of all cited sources and resets the compiled-from set. It never touches the person's sources.

**A note that rebuilds every cycle and comes out materially different each time is a signal.** Either the concept is not atomic and should be split, or the synthesis is unstable. Report it rather than letting it churn.
