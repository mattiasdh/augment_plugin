# Changelog

Dated releases. The semver field in `plugin.json` carries the same date as `year.month.day` so tooling can order it; the form below is the one used for the git tag.

## v2026-09-26

### Improvement

**A near-duplicate is caught before it is minted, not after.** `similar_notes.py` scores a candidate's title and drafted opening against every note with the relations view's own TF-IDF, and PROCESS step 6 and MINT step 2 now run it. The near-duplicate that reached the index on 2026-09-17 scores 0.468 against its original, well past the 0.30 LIKELY SAME line.

**A move that also renamed the file is detected.** When no file keeps the missing source's basename, `detect_changes.py` falls back to a single unindexed file with the same content hash under the same scope path, and still refuses anything ambiguous.

**Procedure-template words no longer count as shared content.** Goal, preconditions, steps and output are in every procedure by construction and kept one generic cluster resurfacing for five nights. Measured against every ruling on record, two more confirmed pairs clear the candidate floor and two fewer declined ones do.

## v2026-09-25

### New feature

**The vault is reachable from Claude Desktop's Chat tab, at full parity.** Chat has no shell, so a Tier 2 (`rules/surfaces.md`) works through two MCP servers on the person's machine. Obsidian's Local REST API reads, searches and writes whole notes, and runs Obsidian Git for pull and commit. `augment-runner`, new and bundled in the plugin, runs the pinned scripts beside the vault, appends to the ledger and holds scratch files. Every operation available in Tier 1 is available there, and the rule maps each one. Setup is in `docs/getting-started.md`.

**The tier is confirmed before any vault work, and a missing one stops the work.** In Code and Cowork, `detect_tier.py` runs as a SessionStart hook and puts one line in context. In Chat, which runs no hooks, the first vault operation of a conversation probes. When neither tier is reachable, the skill names the missing piece and asks the person to connect before going on. A `vault_path` setting lets a Claude Code session opened on another project reach the vault as Tier 1, and the freshness hook follows it there.

**`source_write.py` is the one writer into a person's source, in both tiers.** It sets a system key (status, `created:`, `updated:`, `assisted_by:`) and refuses a write that would move the content hash. It also places a `[!ai]` or `[!note]` callout, and refuses one that would alter existing text. Sessions used to improvise these writes inline, and a surface without a shell could not make them byte-exactly at all.

### Improvement

**Conformance reports a ledger that lost lines.** `ledger_guard.py` checks that `history.jsonl` stayed append-only across the last 200 commits, merges included. The case is not hypothetical. On 2026-09-24 an editor-side merge kept its local tree and dropped a pushed PROCESS pass, twelve ledger lines with it, and no other check could see the loss, because the index recompacted cleanly from what was left. It is an advisory, so the nightly cycle still completes. An entry carrying `"acknowledges": "<sha>"` clears a loss once it is repaired.

### Bug fix

**`rules/write-flow.md` gave `rewrite_check.py` the wrong arguments.** It takes the rewritten file and an optional revision, `HEAD` by default, not an old and a new file.

## v2026-09-24

### Improvement

**The content hash excludes the frontmatter whole.** It used to exclude five named lines, which made every metadata write a hazard: a status write had to be a byte-exact line insert, and giving a bare-form file a fenced block shifted its hash, which happened three times, once reaching the ledger before it was caught. Now the body alone is hashed, so how a source's metadata is written stops mattering. Existing vaults re-stamp once with `migrate_hash_v2.py`.

### New feature

**A cited source carries its backlinks.** `sync_backlinks.py`, run by the nightly cycle after compaction, keeps a `wiki:` line under `augment:` naming the notes that cite the source, mirroring the index as `#linked` does; conformance advises where the two disagree.

### Bug fix

**Conformance reads the bare declaration form**, which it used to flag as untagged, and **its stale-stamp advisory ignores metadata-only edits**, compared by content hash against the file as it stood at midnight, so a status or backlink write no longer reads as the person forgetting to update `updated:`.

### Migrating

Run the cycle first, so no source has drifted, then `migrate_hash_v2.py <vault>` as a dry run, `--apply`, `compact_index.py`, and `sync_backlinks.py`. `detect_changes.py` should report zero drift both after the migration and after the backlinks are written; the second is the test that the writer touched frontmatter only.

## v2026-09-23

### Improvement

**`detect_changes.py` reports a likely rename instead of bare `MISSING`.** Where a missing source's recorded hash matches exactly one current file under its own scope path, it now prints `LIKELY RENAME -> <path>` rather than `MISSING`. This never resolves the rename; recording one stays VERIFY's call. It only saves the sweep from re-deriving the same glob-and-hash check by hand, which an 182-file, 34-source case (2026-09-22) needed a one-off script to do.

**The declared-folder backlog excludes a pending rename's new path.** Without this, a rename's new half could surface as ordinary `#to-process` work and get harvested a second time before VERIFY confirmed the rename, since the old path's `produced` list is never consulted when a different id is read as new.

### Bug fix

**DREAM phase 1 now states a rule for a `#processed` source that drifts with `produced: []`.** It previously had no treatment for this case: the drift-to-`#stale` rule only fires on a non-empty `produced`, and an explicit `#processed` tag sits outside PROCESS's `#to-process` scope regardless of what the content now says, so the source went invisible to every later drift too. Eight occurrences across seven cycles reconstructed the same ad hoc treatment (re-read, decide, re-stamp) from precedent each time. The phase now states it: always re-examine for extraction-worthiness, always re-stamp the hash regardless of the verdict, and report to VERIFY where the content argues for a full re-tag rather than a one-off read.

## v2026-09-16

First release as a plugin. The system ran for two months as a single skill with its contract and operations living inside the vault it governed; this release separates the method from the instance and rebuilds the method around one verb per skill.

### New feature

**Seven skills plus a dispatcher**, each one verb, replacing a router that named ten operations and told the session which prose files to read for each. Three merges: retrieval folded into `answer`, and capture, comment and correction folded into `write`, since all three write into the person's own layer under one set of hard rules and differ only in what they put there.

**Layered loading replaces the tier table.** Each skill names the rules and reference fragments it needs, so a read-only question no longer pays for the compiler's contract. The dispatcher carries the routing table and the hard rules and nothing else.

**Schemas for the ledger.** `index.jsonl`, `history.jsonl` and `config.yaml` now have JSON Schema definitions, so a line can be validated rather than trusted.

**Hooks ship with the plugin**, gated on the vault marker so they exit silently in projects that have no wiki. Previously they lived in one vault's settings and worked only there.

### Improvement

**The contract is decomposed.** What was a single 556-line file covering twelve subjects is seven fragments split on its own section boundaries: layout, note shape, statuses, provenance, links, scope and the ledger, hubs and views.

**The incident record retires.** Its rules were folded into the files that carry them, phrased as rules rather than as dated cases, with a half-sentence of reason only where a rule looks arbitrary without one. Rules superseded since are dropped.

**`config.yaml` gains `plugin_version`**, recording which release last compiled a vault, and conformance compares it against the installed plugin. A mismatch is reported as an advisory rather than compiled over, and a vault declaring nothing is told that a release change cannot be detected for it.

**The layout separates content from method.** Sources move under `notes/`, the wiki becomes `augment_wiki/`, and the two sit beside the plugin at the vault root. `config.yaml` gains `source_root`, which is stripped from every context name and grouping for display, so `sources.md` headings keep the anchors that `further_sources:` points at.

**Three scripts retire.** The skill builder and the skill checker existed to package an unpacked skill into a zip and detect drift between the two; a plugin is the deployable unit, so the class of bug they guarded stops existing. The system exporter filtered a private vault into a public fork of itself, which is what publishing the plugin as its own repository now does structurally.

**The publish guard points at the plugin.** It used to guard a manifest of vault files copied into a public fork. It now guards the plugin tree, which is the surface that actually ships, and the leak terms are still derived at run time from the index rather than written down.

**Conformance becomes a vault check.** The changelog-currency and future-heading checks moved out with the changelog itself, and the write-flow section-reference check reads the rules file from the plugin root while still scanning the vault.

### Bug fix

**The publish guard no longer poisons itself.** It derives part of its denylist from scope-rule paths, so a rule on a structural folder split on the underscore and put the product's own name into the list, after which every published file mentioning it read as a client-identity leak. The product's own name and its directory words are now excluded permanently rather than folder by folder.

**The link example matches the vocabulary.** The contract's own example still showed a link type dropped when the vocabulary went from five types to three. It now uses `related` with the narrower word at the head of the reason line, which is what the rule says to do.

### Migrating an existing vault

Source ids carry the full vault-relative path, so moving the tree rewrites every id in the ledger. **Translate in place rather than starting a fresh ledger**: a genesis snapshot keeps the current state and loses the record of how it got there, which is the one thing an append-only log exists for.

Copy `history.jsonl` aside verbatim first, under a dated name, and never touch it again. Then translate the live copy by whole path values only, never by substring, so a path mentioned inside a `note` field stays as the record of what was written at the time. Append one marker line recording the rule, the archive's hash and its line count.

Three checks say whether it worked. The inverse translation must reproduce the archive byte for byte. `compact_index.py` must rebuild the translated index from the translated history exactly, which is an independent agreement between two files translated separately. And `detect_changes.py` must report **zero drift**: paths changed, content did not, and a single drifting hash would mean a source was touched when it should only have moved.
