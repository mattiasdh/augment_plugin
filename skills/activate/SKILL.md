---
name: activate
description: Start a conversation with the augment vault connected and its memory loaded. Use when the person says activate augment, start augment, load my memory or connect the vault, typically at the start of a Chat conversation, where no session-start hook runs. Confirms the tier, checks freshness, and loads the memory cards that apply. Also turns memory off for the rest of a conversation when the person asks to go off the record.
---

# Activate

**This is the session-start hook for surfaces that run none, and the way in through the connector.** In Code and Cowork, `detect_tier.py` and `memory_context.py` ran at session start and their lines are in context. When they found a local vault (`AUGMENT TIER 1: …`), activating only repeats them, so say so and stop unless the person wants the memory reloaded. When they found none (`AUGMENT: no local vault …`), do not stop there: the session may still reach the vault through the augment connector, so go to step 1. In Chat, nothing ran, and this skill does what the hooks would have done.

## Procedure

**1. Confirm the tier** as `rules/surfaces.md` sets out. When no local tier is reachable and the augment connector's tools are in the session (Chat on the web or the phone, or a Code or Cowork session opened away from the vault), its `activate` tool does steps 1 to 3 at once: call it, and follow the connector's column of the table from then on. Otherwise: `augment-runner` `status`, then `augment_wiki/config.yaml` through the Obsidian MCP. Both must answer. When either fails, name the missing piece and the one step that fixes it, from the gate's list, and stop. A runner absent from a Chat conversation is never fixed by enabling a connector, since the plugin cannot supply it there: the fix is to register it in Desktop's `claude_desktop_config.json`, quit Desktop and open a new conversation.

**2. Check freshness**: `run_script check_freshness`, and `obsidian-git:pull` if it reports behind.

**3. Load the memory**: `run_script memory_context [".", "--project", "<name>"]`, with `--project` when the person names the project the conversation is about, so its cards come first. Keep its output in mind for the rest of the conversation as the hook's line would be in Code. Chat has no per-prompt recall hook, so do its work yourself: before a task that names a tool, a file format, a client convention or a skill, search memory for it (`run_script memory_search`, or `memory_search` through the connector), open the cards that match, and name the card in the reply when it changes what you do. Never ask the person whether to use memory; apply it visibly, and the person overrides it in a word.

**4. Report in two lines**: the tier and the commit the vault is at, and how many memory cards were loaded. Then go on with what the person asked, or wait.

## Off the record

When the person asks to deactivate, pause memory or go off the record, write nothing through `remember` and offer nothing to the source layer for the rest of the conversation, and confirm it in one line. Retrieval stays available. It ends with the conversation; there is no stored switch, because a switch nobody remembers to turn back on silently stops memory for good.

## Never

- Load the memory from a vault whose tier was not confirmed, or from an earlier read in the same conversation after a failure.
- Treat activation as consent to write anything. It connects and loads; every write still goes through its own skill.
