# Session records

**A session record holds where one conversation's work stands, so that another session, on any surface, can pick it up.** It is a handover, written by the model for the model, and kept in the vault because the vault is the one place Chat, Cowork and Code all reach.

## Where and what

`augment_sessions/<id>.md`, one file per conversation, beside `augment_memory/` and outside the source tree, so nothing compiles it into the wiki and no scope rule reaches it. Written only through `record_write.py` (Tier 1 and 2) or the connector's `record_write`; read with `record_write.py get` or `record_get`.

```
---
id: R-261028-k7f3
title: "Harbour: energy memo"
status: open                 # open, parked (paused on purpose) or closed (done)
project: "301 Harbour"       # as the vault names it; optional
surface: chat                # chat, cowork or code
session_id: cse_01…          # the surface's own id, where it has one
created: 2026-10-28 20:00
updated: 2026-10-28 21:15
records: 2                   # how many times this session recorded
by: augment/connector
---
## Goal
## State
## Next steps
## Touched
## Resume
```

The five sections are required, in this order:

- **Goal**: what the conversation set out to do, in a sentence or two.
- **State**: what is done and what was decided, as it stands now. Not the path there.
- **Next steps**: `- [ ]` items, each naming who owes it (the person, Claude, a third party).
- **Touched**: the notes, files, cards, artifacts, branches and links the work used or produced, by path or URL, so a resume can open them.
- **Resume**: a self-contained instruction a fresh session can act on with nothing else: what to open first and what to do next.

## The key

**The id is minted by the first RECORD, never derived from a title.** Chat shows Claude neither its conversation id nor its title, Claude cannot rename a Chat, and the person renames conversations; a title is a label, never a key. The id (`R-YYMMDD-xxxx`) is printed in the reply to every RECORD, and later RECORDs in the same conversation pass it back from context.

- **Code and Cowork**: the session id is stored too (`CLAUDE_CODE_REMOTE_SESSION_ID` where set, else `CLAUDE_CODE_SESSION_ID`), and a RECORD that passes it without an id finds its own record, which survives a compaction. In a Code session the record skill also appends the id to the session's title.
- **Chat**: the person may paste the id into the conversation's title by hand; nothing depends on it.
- **Finding one again** never needs the id: `search` scores the title and project, then the body, so "the Harbour energy one" finds it.

## Supersession

Every RECORD of a session replaces the file; `records:` counts them and git holds every earlier state. A record is current state, so there is no history inside it. Closing (`status closed`) keeps the file; nothing is deleted.

## What never goes in

- **Decisions and findings about the work.** They would matter without Claude, so they are content: they go to the notes through `write` (or `capture_note`), and the record links them under Touched.
- **How a tool behaves.** That is a memory card (`reference/memory.md`).
- **A transcript.** The body stops at 8000 characters.
- **Secrets**, refused by the writer as for memory.

## Who reads it

- **Session start**: `memory_context.py` (and the connector's `activate`) lists the records not closed, newest first.
- **The morning briefing** lists them with their first open next step, stale ones (untouched for `sessions.stale_days`, 14 by default) last.
- **Restore**: the record skill opens one and what its Touched section lists, then carries on from Resume.
