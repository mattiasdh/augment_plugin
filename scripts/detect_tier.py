#!/usr/bin/env python3
"""Which tier this session reaches the vault on, established once at session start.

Run as a SessionStart hook in Claude Code and Cowork, where hooks run; its one
line of output becomes session context, so the skills read the tier from there
instead of probing at every launch (rules/surfaces.md). Chat has no hooks, and
there the gate runs once per conversation from the skill instead.

  Tier 1  the vault is on this machine's disk: the project directory, or the
          plugin's `vault_path` setting, holds `augment_wiki/config.yaml`.
  none    neither. If Obsidian's Local REST API answers on 127.0.0.1:27124 the
          vault is open on this machine but its folder is not set, so the line
          says to set `vault_path` rather than to open Obsidian.

Tier 2 (the Obsidian MCP plus the augment-runner server) is a Chat-tab surface:
wherever hooks run, a shell runs too, and a vault Obsidian can open is on disk,
so Tier 1 is always the better path there.

The Obsidian probe is a liveness check on the unauthenticated root endpoint of a
loopback address; it sends nothing and reads nothing from the vault, so the
self-signed certificate is not verified for it.

    python3 detect_tier.py [--quiet-unless-vault]
"""
import os, ssl, sys, urllib.request

MARKER = os.path.join("augment_wiki", "config.yaml")


def _dir(v):
    v = (v or "").strip()
    return "" if not v or v.startswith("${") else os.path.abspath(os.path.expanduser(v))


def obsidian_up():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        urllib.request.urlopen("https://127.0.0.1:27124/", timeout=1, context=ctx)
        return True
    except Exception:
        return False


def detect():
    project = _dir(os.environ.get("CLAUDE_PROJECT_DIR")) or os.getcwd()
    setting = _dir(os.environ.get("CLAUDE_PLUGIN_OPTION_VAULT_PATH"))
    if os.path.isfile(os.path.join(project, MARKER)):
        return 1, f"AUGMENT TIER 1: the vault is this project ({project}). Scripts run as in the skills, <vault> = {project}."
    if setting and os.path.isfile(os.path.join(setting, MARKER)):
        return 1, (f"AUGMENT TIER 1: the vault is at {setting} (plugin vault_path setting), outside this project. "
                   f"Scripts run with <vault> = {setting}; read and write vault files by that absolute path; "
                   f"git runs there with -C {setting}.")
    if setting:
        why = f"the vault_path setting ({setting}) holds no augment_wiki/config.yaml"
    elif obsidian_up():
        why = "Obsidian is running on this machine but the plugin's vault_path setting is empty"
    else:
        why = "this project is not the vault and no vault_path is set"
    return 0, (f"AUGMENT: no vault reachable in this session ({why}). Work unrelated to the vault proceeds "
               "normally. Before any vault operation, stop and ask the person to connect: open Claude Code "
               "on the vault, or set the augment plugin's vault_path (/config) to the vault folder. "
               "Do not start the operation until a tier is confirmed (rules/surfaces.md).")


if __name__ == "__main__":
    tier, line = detect()
    print(line)
