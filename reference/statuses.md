# Statuses

**The source layer is the person's. The system maintains a source's status line and nothing else:** its body is never edited, and an `#excluded` source is never processed, with no reasoning around it. Wiki statuses, by contrast, are build states the system owns outright.

## Source notes

The first two are the person's declared intent. The rest are written by the system.

| Tag | Meaning | Set by |
|---|---|---|
| `#to-process` | queued for processing | person |
| `#excluded` | never process, permanent exclusion | person |
| `#processed #linked` | processed, and at least one wiki note cites it | `process` |
| `#processed #unlinked` | processed, but no wiki note cites it | `process` |
| `deleted` (index only) | the file was removed from the source tree by the person | `verify` |
| `renamed` (index only) | the path was retired on a rename; a fresh entry carries the new path | `verify` |

The status carries two dimensions so both are filterable at a glance: a **lifecycle** tag and, for a processed source, a **linkage** tag. The linkage mirrors what the index already knows and is duplicated onto the source only so the person can filter unlinked material directly in their editor.

`#excluded` is the confidentiality escape hatch. Client-sensitive material is excluded by declaration, not by hoping the compiler behaves.

**Writing a source's `augment:` field is metadata, not a content edit.** The rule that the system never writes into a source governs the body, the words the person wrote, not the status line. A status line is excluded from the content hash, so setting it changes nothing the wiki depends on, and setting it must still be byte-preserving.

## Renames and deletions

**A source the person renames keeps both paths in the ledger.** The new path gets a fresh entry carrying the old one's hash, processed date and produced list, so nothing reprocesses over a move that changed no content, and the old path is recorded `renamed` with a pointer to the new one rather than dropped. An id here is a path, so a rename is a new id, and recording only the new one would lose the fact that the archive ever held the old.

**A source the person deletes is recorded `deleted`, not dropped.** This is an index state only, since there is no file left to carry a tag, and the entry keeps its last known hash, processed date, produced list and a deletion date. Removing the entry would be the one thing the system never does, because the ledger's value is that it can say what the archive held and when.

The state exists to keep two events apart. A file the person removed is **accounted for**, and once recorded it is not reported again. A file missing and *not* recorded is a finding: a sync that dropped a note, a rename nobody logged, a half-finished move. If every deletion kept announcing itself each cycle, a real loss would sit unread in a standing list of expected ones. So the cycle reports an unrecorded disappearance and the person says which it was; **recording follows their answer and never precedes it.**

Where a deleted source **produced wiki notes**, recording the deletion is not the end of it, because those notes now cite material the archive no longer holds. That is a judgement at the sweep rather than an automatic rebuild, and the honest options differ by case: keep the note and let its citation stand as a record of what was read, rebuild it from the remaining sources, or supersede it. The derived layer must not quietly repair itself around a source the person chose to remove.

## Undeclared

**A source carrying no status tag is undeclared only where no folder rule reaches it.** A `default:` on a scope rule is a declaration the person made for every file under that path, taken once at the folder level instead of file by file, so a file inheriting it is declared and is read without looking for an inline tag. An explicit tag on the file always wins over the default, so a source that must be treated differently from its folder says so on its own line.

What is genuinely undeclared is a source no rule resolves: one in a folder that is in scope but sets no default, or in a folder nobody has ruled on.

Undeclared is never processed and never quietly reclassified. Treating it as `#to-process` would sweep material into the wiki that nobody chose to expose, which in an archive holding client work is the more dangerous error. Treating it as `#excluded` is safer but still wrong, because it converts "not yet considered" into "deliberately excluded", and those two must stay distinguishable.

**Absence of a decision is not a decision.** Count undeclared sources and report them rather than acting on them. Declaration happens in bulk at the sweep, alongside the addresses the person is already assigning.

This matters most at the start. An existing archive is entirely undeclared, so pointing the cycle at one must produce a report of how many sources await declaration, never silence.

## Wiki notes

Build states, not approval states. Nothing here records human endorsement, because there is none.

| Tag | Meaning |
|---|---|
| `#current` | compiled from its sources as they now stand |
| `#stale` | an input changed after compilation, rebuild queued |
| `#flagged` | the person raised an issue, correction pending |
| `#contested` | a tension, deliberately unresolved |
| `#superseded` | replaced, links to the replacement |
