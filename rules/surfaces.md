# Surfaces

**Every operation runs on a confirmed tier, and both tiers can do everything.** The method does not change with the surface; only the hands it works through do. A skill never starts vault work on an unconfirmed tier, and never falls back to a partial mode that quietly skips a script, a ledger write or a push.

## The two tiers

**Tier 1, the filesystem.** A shell next to the vault: Claude Code opened on the vault (on the person's machine or in the cloud), Claude Code in another project with the plugin's `vault_path` set, or Cowork with the vault folder attached. Scripts run as the skills write them, `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<script>.py" <vault> …`, files are read and written directly, and git runs in the vault.

**Tier 2, Obsidian.** No shell, as in the Desktop Chat tab. Two MCP servers stand in for it, on the person's machine:

- **Obsidian's Local REST API MCP**, set up by the person in Desktop (`docs/getting-started.md`): reads, searches, writes whole notes, and runs Obsidian commands, which is how git is reached, through the Obsidian Git plugin.
- **`augment-runner`**, bundled in this plugin: runs the pinned scripts beside the vault, appends to the ledger, and holds scratch files. It needs the plugin's `vault_path` setting.

## The gate

Run it before the first vault operation. How often depends on the surface.

- **Code and Cowork.** A SessionStart hook has already put one line in context: `AUGMENT TIER 1: …` or `AUGMENT: no vault reachable …`. Trust it for the session. Probe again only if a vault call fails.
- **Chat.** Hooks do not run there, so the first vault operation in a conversation probes: call `augment-runner` `status`, then read `augment_wiki/config.yaml` through the Obsidian MCP. Both must succeed. Later operations in the same conversation rely on that result and re-probe only on a failure.
- **Which tier.** A shell plus the vault on disk is Tier 1, and Tier 1 wins whenever it is available. No shell, with `status` READY and Obsidian answering, is Tier 2.

**When the gate fails, stop and ask the person to connect.** Say which piece is missing and the one step that fixes it, then wait, and resume only when the person confirms. The missing piece is one of these:

- Obsidian is not running, or its Local REST API plugin is off.
- The Obsidian MCP is not configured in Desktop.
- `augment-runner` is absent, because the plugin is not enabled on this surface.
- `vault_path` is unset or wrong: set it in the plugin's settings.
- PyYAML is missing for the Python that runs the scripts.

Do not start the operation, and do not answer from memory or from an earlier read, since that is the stale read the freshness rule exists to prevent.

## Doing each thing in Tier 2

| Tier 1 | Tier 2 |
|---|---|
| `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/X.py" <vault> args` | `augment-runner` `run_script`, `script: "X"`, `args: [".", …]`. Paths in arguments are relative to the vault. |
| A scratch file, such as a draft to put through `release_check.py` before it is written | `augment-runner` `scratch_write`, then pass `scratch/<name>` as the argument. |
| Read a file, list a folder | `vault_read`, `vault_get_document_map` |
| Grep across the vault | `search_simple`, or `search_query` for structured queries |
| Write a whole wiki note, new or rebuilt | `vault_write` with the complete content |
| Capture a **new** source note (WRITE capture) | `vault_write` to a path that does not exist yet, frontmatter included |
| Set a source's `augment:`, `created:`, `updated:`, `assisted_by:` | `run_script source_write [".", "set", path, key, value]` |
| Put a `[!ai]` or `[!note]` callout on a source (WRITE comment) | `run_script source_write [".", "callout", path, "--kind", …]` |
| Append to `history.jsonl` | `augment-runner` `append_history`, then `run_script compact_index` |
| `git pull` | `command_execute` `obsidian-git:pull` |
| `git commit` + `git push` | `command_execute` `obsidian-git:commit-and-sync` |
| `git fetch` + compare (freshness) | `run_script check_freshness` (it fetches locally, and never pulls) |

**Never do these in Tier 2:**

- Write an existing source with `vault_write`, `vault_patch` or `vault_append`. The REST API rewrites the file, which is exactly the read-and-rewrite of the person's text the method forbids. Source writes go through `source_write.py` only, which is also the Tier 1 path.
- Append to the ledger with `vault_append`, or write `index.jsonl` at all.
- Use `vault_delete` or `vault_move`. Nothing is deleted, and a rename is the person's act.
- Run `obsidian-git` commands beyond pull and commit-and-sync. Branch, reset, amend and raw-command commands rewrite history the ledger depends on.

## Freshness and the one-writer rule in Tier 2

Freshness is owed per task, as in `rules/freshness.md`:

1. Run `run_script check_freshness`.
2. If it reports behind, `obsidian-git:pull`, then re-run the check.

A writing operation also closes the same way in both tiers:

1. Run `compact_index` and `sync_backlinks`.
2. Regenerate the views.
3. Run `conformance`.
4. Run `obsidian-git:commit-and-sync`, then confirm with `check_freshness` that the working copy is no longer ahead.

Obsidian Git is the only thing that commits in Tier 2. The runner never runs git beyond the fetch inside `check_freshness`, so the repository has one writer on that machine.

**A merge on the editor side can drop the remote's work without a conflict marker.** On 2026-09-24 an Obsidian Git merge kept the local tree whole and lost a pushed PROCESS pass, twelve ledger lines included. `ledger_guard.py`, which conformance runs, reports any commit whose `history.jsonl` lost lines from a parent. A `LEDGER LOSS` advisory goes to the person before anything else:

1. Re-record what the commit dropped, or rule it unnecessary.
2. Append an entry carrying `"acknowledges": "<sha>"`.

## Which surfaces load what

- **Skills** load in Code, Cowork, and Chat on the web and in Desktop.
- **Hooks** run in Code and Cowork only, which is why Chat probes from the skill.
- **Local MCP servers** from the plugin, `augment-runner` among them, run on the machine the client runs on. That is the Mac for Desktop, and never claude.ai on the web.

So Tier 2 is a Desktop surface, and the web Chat has no tier.
