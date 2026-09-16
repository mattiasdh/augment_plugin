# Changelog

Dated releases. The semver field in `plugin.json` carries the same date as `year.month.day` so tooling can order it; the form below is the one used for the git tag.

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
