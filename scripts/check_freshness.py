#!/usr/bin/env python3
"""Is this working copy current with the remote? (CONTRACT §9)

Run this **before reading the vault**, not only before writing to it. The rest
of the staleness machinery answers a different question: `detect_changes.py`
compares each source's stored hash against the file on disk, so it reports which
notes are stale *within this working copy*. Nothing in the index can report that
the working copy itself is behind the vault. The index can be perfectly
consistent and the whole clone three days old.

Reads need this more than writes do, not less. A stale write is caught
downstream (push rejection, conformance, the next rebuild); a stale read is
caught by nothing and leaves as a cited answer the person acts on.

That gap has bitten once on record: a session pulled at its start, worked for
several turns, then read two wiki notes from a three-day-old clone and reported
one of them as citing the wrong source. An upstream pass had already fixed
exactly that two days earlier, so the finding was wrong when it was given, and
the clone's own internal consistency could not reveal it. The push rejection
that followed was the late signal; this script is the early one.

Exit 0 = current, or the remote could not be reached (offline work is allowed,
but it is reported, because "unverified" and "current" are different claims).
Exit 1 = behind, so pull before writing.

USAGE:
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_freshness.py" .
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_freshness.py" . --branch main
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_freshness.py" . --hook   # JSON, for the hook

`--hook` emits the Claude Code UserPromptSubmit envelope instead of plain text,
so the result is injected as context at the top of every turn rather than
depending on the session remembering to ask. Exit stays 0 in hook mode: being
behind is something to tell the turn about, not a reason to kill it.
"""
import json, os, subprocess, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else "."
BRANCH = "main"
if "--branch" in sys.argv:
    BRANCH = sys.argv[sys.argv.index("--branch") + 1]
HOOK = "--hook" in sys.argv
# In hook mode, a session opened on another project still owes the check for the
# vault it reaches through the plugin's vault_path setting (rules/surfaces.md).
_SETTING = os.environ.get("CLAUDE_PLUGIN_OPTION_VAULT_PATH", "").strip()
if HOOK and _SETTING and not _SETTING.startswith("${") and not any(
        os.path.exists(os.path.join(ROOT, p)) for p in ("augment_wiki/config.yaml", "_augment/config.yaml")):
    ROOT = os.path.abspath(os.path.expanduser(_SETTING))


def in_vault(root):
    """True where `root` is an augment vault, by its marker file.

    A plugin-shipped hook fires in every project where the plugin is enabled, so
    each entry point checks for the marker and exits silently when it is absent.
    Without this the freshness hook would fetch in unrelated repositories and the
    register hook would fire in projects that have no wiki. Both layouts are
    accepted while a vault migrates from the older one.
    """
    return any(os.path.exists(os.path.join(root, p)) for p in
               ("augment_wiki/config.yaml", "_augment/config.yaml"))


def git(*args, timeout=60):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, timeout=timeout)


def emit(text, code):
    """Plain text for a human or a script; the hook envelope for the harness."""
    if HOOK:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit", "additionalContext": text}}))
        return 0
    print(text)
    return code


def main():
    if not in_vault(ROOT):
        return 0
    # Fetch rather than pull: this script reports, it never changes the tree.
    # Deciding to merge is the session's, and a pull here would rewrite the
    # working copy out from under whatever is mid-edit.
    try:
        fetched = git("fetch", "origin", BRANCH, "--quiet")
    except subprocess.TimeoutExpired:
        return emit("FRESHNESS: could not reach origin (timeout). "
                    "Working offline against an UNVERIFIED base.", 0)
    if fetched.returncode != 0:
        err = (fetched.stderr or "").strip().splitlines()
        return emit(f"FRESHNESS: could not reach origin "
                    f"({err[-1] if err else 'fetch failed'}). "
                    f"Working offline against an UNVERIFIED base.", 0)

    behind = git("rev-list", "--count", f"HEAD..FETCH_HEAD").stdout.strip()
    ahead = git("rev-list", "--count", f"FETCH_HEAD..HEAD").stdout.strip()
    behind = int(behind) if behind.isdigit() else 0
    ahead = int(ahead) if ahead.isdigit() else 0

    if behind:
        # Name the files, because "3 commits behind" does not tell a session
        # whether the drift touches what it is about to read or write.
        # splitlines, not split: this archive is full of filenames with spaces,
        # and whitespace-splitting turns one path into a column of fragments.
        names = [n for n in git("diff", "--name-only",
                                "HEAD..FETCH_HEAD").stdout.splitlines() if n.strip()]
        shown = "\n".join(f"  ~ {n}" for n in names[:20])
        if len(names) > 20:
            shown += f"\n  ~ (+{len(names) - 20} more)"
        return emit(
            f"FRESHNESS: BEHIND origin/{BRANCH} by {behind} commit(s)"
            + (f", ahead by {ahead}" if ahead else "") + "\n" + shown
            + f"\nPull before reading or writing the vault: "
              f"git pull --no-rebase origin {BRANCH}", 1)

    return emit(f"FRESHNESS: current with origin/{BRANCH}"
                + (f" (ahead by {ahead}, unpushed)" if ahead else ""), 0)


if __name__ == "__main__":
    sys.exit(main())
