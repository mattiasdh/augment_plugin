# Surfaces

**Every operation runs on a confirmed tier, and both tiers can do everything.** The method does not change with the surface; only the hands it works through do. A skill never starts vault work on an unconfirmed tier, and never falls back to a partial mode that quietly skips a script, a ledger write or a push.

## The two tiers

**Tier 1, the filesystem.** A shell next to the vault: Claude Code opened on the vault (on the person's machine or in the cloud), Claude Code in another project with the plugin's `vault_path` set, or Cowork with the vault folder attached. Scripts run as the skills write them, `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/<script>.py" <vault> …`, files are read and written directly, and git runs in the vault.

**Tier 2, Obsidian.** No shell, as in the Desktop Chat tab. Two MCP servers stand in for it, on the person's machine:

- **Obsidian's Local REST API MCP**, set up by the person in Desktop (`docs/getting-started.md`): reads, searches, writes whole notes, and runs Obsidian commands, which is how git is reached, through the Obsidian Git plugin.
- **`augment-runner`**, a script in this plugin (`scripts/runner_mcp.py`): runs the pinned scripts beside the vault, appends to the ledger, and holds scratch files. **Chat never starts a plugin's own MCP server**, so there the person registers the runner by hand in Desktop's `claude_desktop_config.json`, beside the Obsidian entry, pointing at a clone of the plugin and giving the vault as `AUGMENT_VAULT` (`docs/getting-started.md`). The plugin starts it itself only in Code and Cowork, where it reads the plugin's `vault_path` setting.

## The gate

Run it before the first vault operation. How often depends on the surface.

- **Code and Cowork.** A SessionStart hook has already put one line in context: `AUGMENT TIER 1: …` or `AUGMENT: no vault reachable …`. Trust it for the session. A second hook has loaded the memory cards that apply (`reference/memory.md`). Probe again only if a vault call fails.
- **Chat.** Hooks do not run there, so the first vault operation in a conversation probes, or the person starts with `activate`, which also loads the memory: call `augment-runner` `status`, then read `augment_wiki/config.yaml` through the Obsidian MCP. Both must succeed. Later operations in the same conversation rely on that result and re-probe only on a failure.
- **Which tier.** A shell plus the vault on disk is Tier 1, and Tier 1 wins whenever it is available. No shell, with `status` READY and Obsidian answering, is Tier 2.

**When the gate fails, stop and ask the person to connect.** Say which piece is missing and the one step that fixes it, then wait, and resume only when the person confirms. The missing piece is one of these:

- Obsidian is not running, or its Local REST API plugin is off.
- The Obsidian MCP is not configured in Desktop.
- `augment-runner` is absent from the conversation. In Chat it is never supplied by the plugin: it must be registered in `claude_desktop_config.json`, then Desktop quit fully and a new conversation opened, since connectors attach when a conversation starts. There is no toggle to enable it otherwise.
- The runner reports no vault: `AUGMENT_VAULT` in Desktop's config (Chat) or the plugin's `vault_path` (Code, Cowork) is unset or wrong.
- PyYAML is missing for the exact Python that runs the runner. On macOS that is usually `/usr/bin/python3`, and the fix is `/usr/bin/python3 -m pip install --user pyyaml`; pipx does not make it importable.

Do not start the operation, and do not answer from memory or from an earlier read, since that is the stale read the freshness rule exists to prevent.

## Doing each thing in Tier 2, and through the connector

The remote connector (`connector/`, for Chat on the web and the phone) is the third column: the same actions, the same rules, over GitHub. It has every file primitive Tier 2 has; what it lacks is a script runner, since a Cloudflare Worker cannot run the plugin's Python. The two script writers every write path depends on, `source_write.py` set and callout, are ported into it and held to the Python by parity tests, as `memory_write.py` is.

| Tier 1 | Tier 2 | Connector |
|---|---|---|
| `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/X.py" <vault> args` | `augment-runner` `run_script`, `script: "X"`, `args: [".", …]`. Paths in arguments are relative to the vault. | Not available. Say so, and name the surfaces that can: a Claude Code session on the vault (also from the Claude app, in the cloud), Cowork, or Desktop Chat with the runner. |
| A scratch file, such as a draft to put through `release_check.py` before it is written | `augment-runner` `scratch_write`, then pass `scratch/<name>` as the argument. | Not available (no scripts to pass it to). |
| Read a file, list a folder | `vault_read`, `vault_get_document_map` | `vault_read`, `vault_list` |
| Grep across the vault | `search_simple`, or `search_query` for structured queries | `vault_search` (titles, aliases, keywords, summaries, source paths; not full text) |
| Write a whole wiki note, new or rebuilt | `vault_write` with the complete content | `vault_write`; in practice only inside process or mint, which need scripts |
| Capture a **new** source note (WRITE capture) | `vault_write` to a path that does not exist yet, frontmatter included | `vault_write` to a new path, frontmatter included, or `capture_note` for the inbox |
| Set a source's `augment:`, `created:`, `updated:`, `assisted_by:` | `run_script source_write [".", "set", path, key, value]` | `source_set` |
| Put a `[!ai]` or `[!note]` callout on a source (WRITE comment) | `run_script source_write [".", "callout", path, "--kind", …]` | `source_callout`, which also parks the comment's ledger entry |
| Change a skill's rule (`reference/skills.md`) | `vault_write` of the reference file, its CHANGELOG line with it | `vault_edit` (one exact passage) or `vault_write`, with `changelog`: one commit |
| Append to `history.jsonl` | `augment-runner` `append_history`, then `run_script compact_index` | `append_history`, parked in `augment_wiki/history.pending/` because GitHub cannot append; `compact_index.py` merges it at the next script-capable run |
| `git pull` | `command_execute` `obsidian-git:pull` | Not needed: every read is the GitHub head. |
| `git commit` + `git push` | `command_execute` `obsidian-git:commit-and-sync` | Not needed: every write is one commit, made against the head it read. |
| `git fetch` + compare (freshness) | `run_script check_freshness` (it fetches locally, and never pulls) | Not needed; edits not yet synced from Obsidian are not visible, and `activate` says so. |
| Write, confirm or supersede a memory card | `run_script memory_write [".", "add", …]`, never `vault_write` into `augment_memory/` | `memory_add`, `memory_seen`, `memory_update`, `memory_supersede`, never `vault_write` into `augment_memory/` |
| Search memory, load it at the start of a conversation | `run_script memory_search [".", words…]`; `run_script memory_context [".", "--project", name]` | `memory_search`; `activate` |

**Never do these in Tier 2 or through the connector.** The connector refuses each in code; in Tier 2 they rest on this rule.

- Write an existing source with `vault_write`, `vault_patch`, `vault_append` or `vault_edit`. Rewriting the file is exactly the read-and-rewrite of the person's text the method forbids. Source writes go through `source_write.py` only (in the connector, its ports `source_set` and `source_callout`), which is also the Tier 1 path.
- Append to the ledger by editing `history.jsonl`, or write `index.jsonl` at all.
- Delete or move anything (`vault_delete`, `vault_move`). Nothing is deleted, and a rename is the person's act.
- Write into a folder `config.yaml` ignores, rules out or has not ruled on, except the declared skills root and the inbox.
- Run `obsidian-git` commands beyond pull and commit-and-sync (Tier 2). Branch, reset, amend and raw-command commands rewrite history the ledger depends on.

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
- **Local MCP servers** from the plugin, `augment-runner` among them, run in Code and Cowork only, never in Chat. Desktop Chat reaches a local server only through Desktop's own config, which is why the runner is registered there by hand.

So Tier 2 is a Desktop surface built from two hand-registered servers, and the web Chat has no local tier. The remote connector (`connector/`) serves the web and the phone with the same file primitives and rules as Tier 2, over GitHub, without the script runner. Script-built operations from the phone go to a Claude Code session on the vault, which runs as Tier 1 in the cloud.
