# Freshness

**Verify freshness against the remote before acting on vault content, reading as much as writing.**

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_freshness.py" <vault>
```

The vault syncs from several directions at once: the owner's editor, mobile sync, the nightly cycle, another session. A working copy therefore goes stale while a session is still inside it, so pulling once at the start settles nothing about the turn you are in. The check is owed per task, not per session.

The script fetches and reports, exiting non-zero when behind and naming the files that moved, since a commit count alone does not say whether the drift touches what is in hand. It fetches rather than pulls, so it never rewrites a tree that may be mid-edit. Pull when it reports behind, then re-run it immediately before any push.

**The read case is the worse one.** A stale write is caught downstream: the push is rejected, conformance runs, the next cycle rebuilds. A stale read is caught by nothing. It leaves as an answer, with citations, and the person acts on it. Every skill that reaches a conclusion from vault content owes this check, which is all of them.

The index cannot answer this question. It reports staleness inside this working copy and can say nothing about the copy being behind the vault.
