# Scripts

Deterministic implementations, **run and never read into context**. Every one takes the vault root as its first argument, so `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py" .` from the vault root is the shape of every call. Read a script only to debug the script itself.

## Checks

| Script | What it does |
|---|---|
| `check_freshness.py` | Whether the working copy is behind the remote. Exits silently outside a vault, so it is safe as a global hook. `--hook` prints JSON. |
| `detect_changes.py` | Re-hashes every indexed source against its recorded hash: drift, missing, retired. The staleness detector. |
| `conformance.py` | The wiki-integrity gate. Exit 1 on defects, advisories are non-blocking. Run before every commit. |
| `hash_source.py` | One file's content hash. The byte rule is exact; never reimplement it. |
| `release_check.py` | Typography and register on a file about to be released. |
| `rewrite_check.py` | What a rewrite actually changed, against a revision or a section. |
| `write_flow_register.py` | Re-asserts the writing register on a prose-shaped prompt. Hook only. |

## The ledger

| Script | What it does |
|---|---|
| `compact_index.py` | Rebuilds `index.jsonl` from `history.jsonl`, last entry per id. **Never hand-edit the index**; append to history and run this. |
| `apply_keywords.py` | Applies keyword and anchor writes to note bodies and records them. `--auto --run <id> --reason` marks an unattended write. |
| `undo_run.py` | Reverts every write a run made. `--dry-run` first; `--only slugA::slugB` for a single one. |
| `dismiss_pairs.py` | Appends declined convergence pairs to the sidecar, so a rejected pair does not resurface. |
| `restyle_queue.py` | Tracks which notes a writing-rule change has already been rebuilt under. |
| `sync_backlinks.py` | Keeps each cited source's `wiki:` frontmatter line in step with `produced`. Run after compaction; frontmatter only, hash-checked per file. |
| `migrate_hash_v2.py` | One-time: re-stamps a vault's ledger from the pre-v2026-09-24 hash to the frontmatter-excluding one. Dry run by default; refuses while any source has drifted. |

## Generators

Each rewrites one derived file and prints a one-line summary. None of them decides anything; they project the index.

| Script | Writes |
|---|---|
| `gen_hubs.py` | `hub/`, one per type and kind, plus `hub.md` |
| `gen_themes.py` | theme bodies, from the notes anchored to each |
| `gen_sources.py` | `view/sources.md`, the index into the source layer |
| `gen_timeline.py` | `view/timeline.md`, dated decisions per project |
| `gen_relations.py` | `view/relations.md`, the relationship overlay and the candidate lanes |
| `gen_verify_queue.py` | the generated half of `verify-queue.md` |

`_gen_util.py` and `_publish.py` are imported, not invoked: shared front-matter, config and scope helpers, and the definition of what the plugin publishes.
