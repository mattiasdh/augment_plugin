# Changelog

Dated releases. The semver field in `plugin.json` carries the same date as `year.month.day` so tooling can order it; the form below is the one used for the git tag. A second release on the same day adds a revision letter: `v2026-09-29 Rev. A` here, `2026.9.29-revA` in `plugin.json`.

## v2026-10-09

### Bug fix

**A rename that was also edited is reported, and an empty alias answer is remembered.** `detect_changes.py` now reports a missing source as `LIKELY RENAME (edited)` when exactly one unindexed file under its scope path keeps at least 80% of its lines, read from git, and anything ambiguous stays `MISSING`; the exact-hash test could not see a file renamed with lines added. The alias backfill left no mark on a note whose sources offer no second name, so the same notes headed the oldest-first order every night: an empty answer is now recorded in `augment_wiki/aliases_checked.jsonl`, `apply_aliases.py --next` lists the notes still to read, and conformance no longer counts a recorded note until it is recompiled.

## v2026-10-06

### Bug fix

**`--help` is help in every script that takes a vault.** The scripts read their first argument as the vault path, so `detect_changes.py --help` failed on `--help/augment_wiki/index.jsonl` and `gen_relations.py --help` regenerated a view as a side effect. A new shared `_cli.py` makes `-h` and `--help` print the script's own docstring and exit before anything is read or written, and a script that takes only a vault now refuses an unknown leading flag instead of treating it as a path.

## v2026-10-05 Rev. A

### Bug fix

**The connector is a tier.** The tier gate in `rules/surfaces.md` knew only the vault on disk (Tier 1) and Obsidian with the runner (Tier 2). So in a session where the plugin's hooks run, opened away from the vault, "activate" stopped at the hook's "no vault reachable" even with the connector connected and working (2026-10-05).
- The gate now tries Tier 1, then Tier 2, then the connector, whose `activate` is the probe.
- The hook's line now reads "no local vault" and names the connector route.
- `activate` goes on to the connector instead of stopping.
- The gate fails only when none of the three answers, and its list of fixes names connecting the connector.

## v2026-10-05

### Improvement

**The connector's `activate` names every tool it serves**, and tells the model what a missing one means: claude.ai keeps the tool list it read when the connector was added, so tools from a later redeploy stay invisible until the connector is reconnected. A chat on a stale list now asks for the reconnect, where on 2026-10-05 it reached for the Obsidian server's `vault_list` instead.

## v2026-10-03 Rev. A

### Bug fix

**Conformance's stale-stamp advisory no longer reads a moved file as a changed one, and reads accented file names.** A file moved today is now compared with its version at the old path at midnight, found through git's rename detection, so a pure move is silent while a move with an edit, or a plain edit, still reports. Git had been writing accented paths escaped, so an edited note with an accent in its name never matched the check; it now does.

## v2026-10-03

### Bug fix

**`release_check.py` finds the vault from the files it checks, not from where the script sits.** It assumed the plugin lived four folders inside the vault, so every installed copy, and every run through the Tier 2 runner, reported each wikilink as resolving to no file. It now looks above the files, then above the working directory, and with no vault says the wikilinks were not checked.

## v2026-10-02 Rev. A

### New feature

**The connector works under the same rules as every other surface, with the same file primitives as Tier 2.** `rules/surfaces.md` gains a Connector column beside Tier 1 and Tier 2, under one Never list that the connector also checks in code. New tools:
- `vault_list`: a folder's notes and subfolders, as far as the reading rules open it.
- `vault_write`: a whole note; never an existing source.
- `vault_edit`: one exact passage of a skill's file, with its CHANGELOG line.
- `source_set` and `source_callout`: ports of `source_write.py` `set` and `callout`, held to the Python by parity tests on LF, CRLF, BOM, bare-form and untitled files, and to `hash_source.py` for the content hash.
- `append_history`: ledger entries, parked in `augment_wiki/history.pending/`, because GitHub cannot append to a file. `compact_index.py` now merges them first, and DREAM runs it as phase 0.

Every connector write is one commit against the head it read, through GitHub's `createCommitOnBranch`; a memory card and its index now land together. What the connector still cannot do is run scripts, so process, mint and dream say so through it and name the surfaces that can, a Claude Code session on the vault from the Claude app among them.

### Improvement

- The per-prompt recall counts generic vault and tool words ("connector", "write", "file", "note"...) at a third, so they confirm a card but cannot carry it alone. "Can the connector write files" no longer names the Coda card.
- DREAM rebuilds the upload packages of vault-held skills nightly (`package_skill.py --all`).
- Conformance reports parked ledger files.

## v2026-10-02

### New feature

**Every memory card reaches the session, and the ones a prompt is about are named.** Session start (`memory_context.py`, and the connector's `activate`) now lists every active card, project-scoped first, then global, then cards scoped elsewhere. Scope orders the list and labels the card; it no longer filters. Before this, a card scoped to a client or a skill matched no session at all: a Code session is opened on the vault and Chat names no project, so on 2026-10-02 the socials and fee-table cards had never been loaded. `memory_recall.py`, a new UserPromptSubmit hook, names up to three cards the prompt is about by its rare words in their titles, keywords and summaries, and stays silent on a prompt that matches nothing distinctive. In Chat, `activate` and the connector's instructions ask for the same search before any task that names a tool, a format or a skill. Nobody is asked whether to use memory; the card is applied and named.

**Skills can keep their rules in the vault.** `config.yaml` declares a skills root (`skills: root:`). Each skill there has its own folder: a thin SKILL.md, the `references/` it reads live on every use, a CHANGELOG.md of approved rule changes, and `dist/<skill>.skill`, which the new `package_skill.py` builds for upload deterministically. The root stays out of the wiki's scope. The connector's `vault_read` reads it anyway, so a skill on the phone reads the same rules as one in Code. Feedback that changes a rule is proposed as lines and applied on approval: from Code to the file, from Chat as a `memory_offer` correction that the sweep applies. It is never a memory card. Conformance reports skill-folder problems as advisories. `reference/skills.md` holds the convention.

### Improvement

**The memory writers refuse the shapes that turned a card into a second copy of a skill.**
- A body over 3,000 characters is refused, in Python and in the connector alike; every legitimate card in the vault is under it.
- Every card write regenerates `index.md`, from one renderer shared by both writers and pinned by a parity test, so the index never shows a summary the card no longer has.
- `gen_memory_index.py` flags as UNSTABLE a card edited more than three times in seven days, and `verify` rehomes what keeps moving.
- `remember` gains a split act: a lesson that carries a fact becomes a method card plus an offer of the fact.
- Python offers take `--kind` and `--target`, as the connector's do.

**One front door each way.**
- `answer` runs the memory search beside the vault search when a question is also about how the work was done, under its own heading and never as evidence.
- `write` owns a rule the person sets for a skill's output, as an approved edit to that skill's reference file; `remember` sends it there.
- `verify` opens with five lines of what Claude learned that week.
- The routing tests gain three "keep this" cases: one content, one method, one skill rule. On 2026-10-02 the default model routed all 44 correctly. On the first run, the skill-rule case ("keep that rule for the socials") went to `remember`; `write` now owns a rule set for a skill's output, as an approved edit to that skill's reference file.

## v2026-09-29 Rev. A

### New feature

**A capture is checked against the vault before it is filed.** `similar_notes.py --sources` scores a draft against in-scope sources and the inbox as well as the wiki, never reading an out-of-scope, unruled or ignored folder, and WRITE capture runs it as step 0, offering a comment on the existing source instead of a second copy. The source cut-offs were calibrated on the vault itself: an exact copy scores 0.99, a two-sentence paraphrase 0.45, new material under 0.15, and from 0.60 up the best match between existing sources was almost always a real duplicate (a sync-conflict copy, a `-AA-mdh` twin, a v2 beside its v3).

**Wiki notes carry the names their sources use.** `aliases:` holds two to four names, each found in one of the note's own sources, so a note titled in English is found by the Dutch or French its sources use. `apply_aliases.py` is the only writer and refuses a name no source carries; PROCESS sets them on new and rebuilt notes, DREAM phase 6 backfills twenty a night, and conformance counts what is left (185 notes at release).

**A search index for searches that cannot open files.** `gen_search.py` writes `augment_wiki/search.json` at the end of DREAM phase 7: titles, aliases, keywords, a one-line summary and cited sources per note, and the in-scope sources with the notes citing them, already tokenised. The connector's `vault_search` reads it, and its `capture_note` names likely duplicates.

**Routing tests for the skills.** `evals/routing/` holds 41 requests, three or four per skill, phrased the way a person would type them, graded on which skill Claude loads, with the memory/content boundary weighted in: a client's requirement must reach `write` and not `remember`, a tool quirk `remember` and not `write`. Run with `claude plugin eval . --ablation none --tag routing --scaffold`. On 2026-09-29 the default model routed all 41 correctly; Haiku routed 23, confusing the sweep with the nightly cycle, recall with answer, and a client's drawing convention with the person's own. Those descriptions are sharpened in this release, below, and the suite is the check.

### Improvement

**Eight skill descriptions name their neighbours**, against the routing tests: the weekly sweep is `verify`, not `dream`; digesting particular sources is `process`; how Claude did something before is `recall`, not `answer`; a client's or project's requirement is `write`, not `remember`. The default model routes all 41 test requests correctly before and after; Haiku went from 23 to 26.

**Accents fold in the memory tokeniser**, so `réemploi` and `reemploi` are one word; no card's duplicate report changes.

**One resolver for source ids**, `_gen_util.source_path`, used wherever a script opens a source by id. No behaviour change; it is where a later read-only mounted source root would be resolved.

## v2026-09-29

### Improvement

**The sweep sees the memory layer's state even on a night the cycle skips it.** `gen_verify_queue.py` now writes a generated Memory section from `gen_memory_index.py --check`, so `LIKELY SAME`, `DECAY`, `OFFER` and `DEFECT` lines reach the queue on every regeneration; on 2026-09-28 and 2026-09-29 the nightly cycle skipped phase 7b and nothing showed it.

## v2026-09-28

### Bug fix

**Desktop Chat never starts a plugin's own MCP server, so `augment-runner` is registered there by hand.** `rules/surfaces.md`, `activate` and the Desktop section of `docs/getting-started.md` had said the plugin supplied it and sent a missing runner to a connector toggle that cannot exist; they now give the working setup: a clone of the plugin, the runner in `claude_desktop_config.json` with full paths, PyYAML for the exact interpreter with `pip install --user` rather than pipx, and a terminal test before Desktop.

### New feature

**A remote connector for the web and the phone.** `connector/` is a Cloudflare Worker that serves the vault over MCP to Claude on the web and the mobile apps, through GitHub. It loads and writes memory with the same refusals as `memory_write.py`, searches wiki titles and source paths, reads what the vault's own scope rules allow at request time, and captures create-only into the inbox; comments and corrections are parked as offers for the sweep. GitHub sign-in proves identity only, a fine-grained token limited to the one repository does the reading and writing, and tokens are issued only to Claude's callback hosts. The memory and scope logic is ported from the scripts, and parity tests run the Python beside the port. Deploying it changes nothing in the plugin as installed; it shipped ahead of this release, which names it in `rules/surfaces.md` as the route for the web and the phone.

## v2026-09-27

### New feature

**A memory layer for how the work is done, kept apart from what the archive says.** `augment_memory/` sits beside the wiki and holds cards of four types: how a tool, connector or MCP server really behaves, the person's output and file conventions, reusable snippets, and working procedures. The boundary is one test, whether the thing would still matter without Claude; anything that would is content and is offered to the source layer as an assisted note instead, so memory never duplicates the notes. It has no ledger, since nothing is compiled from it, and its generated `index.md` stays separate from the wiki's. The contract is `reference/memory.md`.

**Three skills work it.** `remember` writes a card through `memory_write.py`, which refuses a near-duplicate of an active card and names it, so relearning something reinforces the existing card instead of adding a second. `recall` searches the cards with `memory_search.py`. `activate` does in Chat what the hooks do in Code: confirms the tier, checks freshness and loads the memory, and takes a conversation off the record on request.

**The cards that apply are loaded at session start, and again after a compaction.** `memory_context.py` runs as a second SessionStart hook, puts cards scoped to the project the session is opened on first, then global ones, within a 6,000-character budget. It is silent outside a vault.

**The cycle consolidates memory; the sweep decides what leaves it.** DREAM phase 7b regenerates the index, merges likely-same pairs by supersession and reports decay proposals and waiting offers. VERIFY step 2b routes offers into the source layer through `write` capture, archives what decayed, and proposes a settled preference for the person's standing preferences and a reused snippet as a skill.

### Improvement

**`augment_memory/` is structural, like `augment_wiki/`.** It is never counted as undeclared, never listed as an undecided folder, never a source to conformance, and `source_write.py` refuses to write into it.

### Configuring

An optional `memory:` block in `config.yaml` overrides the defaults: `enabled` (true), `index_cap` (150 index lines), `inject_chars` (6000) and `decay_days` (180). Without it, memory runs on the defaults as soon as the first card is written.

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
