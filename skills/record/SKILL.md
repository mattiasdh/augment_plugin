---
name: record
description: Save where this conversation's work stands as a session record, and pick saved work up again later from any surface. Use when the person says record, save the session, save state, handover, park this, I want to come back to this later, or at the end of a long working session they may resume; and to restore, resume or continue earlier work ("where were we on the Harbour memo", "restore R-261028-k7f3", "what did I leave open"). Also closes or parks a record. Not how a tool behaves, which is remember, and not a decision or finding about the work, which is write.
---

# Record

**A record is the handover a fresh session needs to carry on: goal, state, next steps, what was touched, and how to resume.** Read `reference/sessions.md` before the first RECORD of a conversation; it holds the shape, the key and what never goes in.

Confirm the tier as `rules/surfaces.md` sets out. In Tier 1 and 2 everything below is `record_write.py`; through the connector it is `record_write`, `record_get` and `record_search`.

## Which act

| The person wants | Act |
|---|---|
| to save where this conversation stands (first time) | `write` without an id; quote the minted id in the reply |
| to save again later in the same conversation | `write --id <the id quoted earlier in this conversation>`: it replaces the state |
| to pause the work on purpose, or say it is done | `status <id> parked` or `status <id> closed` |
| to resume earlier work | `search <words>` (or `list`), `get <id>`, then restore as below |
| to see what is open | `list` |

**Find the id before writing.** Look back through this conversation for an id a RECORD already returned. In Code and Cowork, pass the session id as well (`CLAUDE_CODE_REMOTE_SESSION_ID`, else `CLAUDE_CODE_SESSION_ID`, from the environment): with it, a RECORD after a compaction finds its own record without the id. Never guess an id; when unsure, `search` first.

## Writing the state

Write the body from the conversation as it stands, never from memory of earlier records:

```
## Goal
## State
## Next steps
- [ ] <owner>: <step>
## Touched
## Resume
```

- **Goal and State are short.** What was decided goes to the notes first, through `write` with the person's agreement, and the record links that note under Touched. If something decided has not been captured, offer the capture before recording.
- **Next steps name who owes each one**: the person, Claude, or a third party by role.
- **Touched lists paths and URLs**: vault notes by full path, files, artifacts, branches, pull requests, memory cards applied.
- **Resume is an instruction a fresh session can act on alone**: what to open first, what to do next, what to check before continuing.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/record_write.py" <vault> write \
  [--id R-…] --title "Short name of the work" [--project "301 Harbour"] \
  --surface code --session-id "$CLAUDE_CODE_REMOTE_SESSION_ID" \
  --body-file <draft> --by <producer>/<version>
```

`--by` is read from the runtime as `reference/provenance.md` sets out. In Tier 2 write the draft with `scratch_write` and pass `scratch/<name>`.

Reply in two lines: the id (so the person can quote it anywhere, or paste it into a Chat title), and whether this created the record or replaced version n. In a Code session where `set_session_title` is available, append ` [<id>]` to the session's title on the first RECORD, keeping the title otherwise as it was.

## Restoring

1. `search` with the words the person uses (project, subject, a file name, a date), or the id when they have it. Several hits: show the top three as one line each and let the person choose.
2. `get <id>`, then open what Touched lists that this surface can reach: vault notes through `answer`'s reads, files and branches where the session has them. Say in one line what could not be opened here.
3. Summarise the state and the next steps in a few lines, then carry on from Resume. The work continues in this conversation; when it is recorded again, pass the same id, so the record moves with the work.

## Committing

`RECORD: <id> <title>` touching only `augment_sessions/`, with the `Assisted-by:` trailer; a status change is `RECORD: <id> <status>`. The connector commits for itself. A record is the session's own write, so it commits even in a session that changed nothing else.

## Never

- Record when the person asked to stay off the record.
- Put a decision, a finding, a client's requirement or anything else that would matter without Claude in the record alone. It goes to the notes; the record links it.
- Write into `augment_sessions/` by hand, or delete a record. Close it.
- Reuse an id from another conversation's record to write this one's state, unless the person is resuming that work here.
