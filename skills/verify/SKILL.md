---
name: verify
description: The weekly sweep, and the only operation needing the person present. Use when someone asks for the sweep, the weekly review, to go through the queue, or to audit what the nightly cycle has been doing. Audits the writes the cycle made unattended, then takes the decisions the cycle is barred from making alone: removals, splits, supersessions, tensions, and anything in the person's own layer.
---

# Verify

Orchestration rather than a new capability. It reads what the cycle did, audits it, and takes the decisions the cycle may not take alone.

**It is not a confirmation queue.** The cycle anchors the notes it writes, applies the convergence verdicts it is sure of, and mints the node a cluster deserves, all without asking. So the first question is not which of these do you approve but **is anything here wrong**. A sweep that finds nothing wrong and has no decision to take says so in a few lines and ends, which is the system working rather than the sweep failing.

Target about fifteen minutes, and the audit should make it shorter rather than longer. If it regularly runs longer, the system is taking more than it gives, so say so rather than letting it creep.

Read `reference/scope-and-index.md` and `reference/views-and-hubs.md`, plus `rules/cognition.md` §§4 and 6. This skill compiles nothing, so the sections governing how a note is written are opened only when a specific rule is in question. Where a sweep does hand-write a note, and a sourced-link escalation is the standing case, read `reference/note-shape.md` for that write.

## Duties in force

- **Be a partner, not a mirror.** Report the state honestly, including when the honest report is that the system is not working.
- **Append, never blank.**
- **Never interpret silence as assent.**

## Procedure

**1. Answer the folders, then declare the sources inside them.** Two decisions in that order, because the second is meaningless until the first is settled.

Folders awaiting a decision are the generated list at the top of the queue: top-level folders no scope rule touches, which is to say nobody has ever been asked about them. Put each to the person with its file count and take an answer, in scope with a default or out of scope. Either answer is written to `config.yaml` and takes the folder off the list for good. **Ask about a new folder the sweep it first appears**, rather than letting it sit as a number in the census, since the whole point of the third state is that "not yet asked" stops being indistinguishable from "already declined". A folder that is scratch rather than knowledge goes to the ignore list and is never counted again.

Where the vault holds no source folders at all, ask where the person's notes should live and record the answer. Do not create a tree on a guess: a structure guessed at setup is the hardest of all to undo, since everything filed afterwards inherits it.

Then, within the folders now in scope, the cycle reports how many sources carry no status. Present them grouped by folder and take a decision in bulk, whole folders at a time rather than note by note. Declaring writes only the status line, does not touch the timestamps and does not change the content hash, so retagging a source that is already processed rebuilds nothing.

**2. Triage the inbox.** Propose a destination for each item; the person assigns the address. Discard what will not be returned to.

**3. Read the queue, conformance findings first. Then audit what the cycle wrote.** The applied-writes section lists every autonomous tag, anchor and mint since the last sweep, one line each under its run id, and conformance counts them independently and advises when a note gained six or more unattended, which is what an over-eager anchoring pass looks like from outside.

Read the lines, not the count. Anything wrong comes out with the undo script, a whole night by run id or one write with `--only`, and the revert is recorded as an ordinary confirmed removal.

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/undo_run.py" <vault> <run-id> [--only slugA::slugB]
```

**Read a sample rather than every line once the list runs long, and say that is what you did.** An audit claimed over twenty lines and actually done over three is worse than an honest spot-check, because it retires the finding without having looked.

**4. What is left is the judgement the cycle is barred from**: what to take away, what to split, what to supersede, what to contest, and everything in the person's own layer.

**5. Confirm everything else in batch**: merges, splits, tension notes, supersessions, and any system change the cycle proposed. Work the system-observations list the same way, taking a decision on each, applying what is confirmed and striking what is declined so it is not re-proposed. Nothing touching a rule, a skill or a script is integrated without sign-off here.

Before signing off a fix, test it against `rules/cognition.md` §6: does it repair the cause or the symptom, and if a rule already existed, does the fix change where that rule is read rather than only how firmly it is worded? Any confirmed change to the plugin is logged the same session in its changelog, dated, at most two sentences. A new feature or substantial improvement also gets a docs pass; a bug fix does not.

**An empty convergence batch is the healthy state, and a full one is the finding.** What reaches this list is only what the cycle **held**, so empty means it judged its slice cleanly and the audit in step 3 is where the reading goes. The signal inverts: a cycle holding most of its slice, or holding the same item across several sweeps, is the thing to ask about, because either the material got harder or the cycle stopped deciding.

## How the batch is put

**Present the whole batch as one numbered list, written out in full in the reply itself.** Every item spelled out where the person is reading, both notes named and the reason given, never abbreviated to a count, a range, a sample or a pointer to the queue file. A batch summarised as "items 1 to 15, listed in the queue" is not a batch that was presented: the person cannot judge what they cannot see.

**The batch means every open item, not the ones drawn this cycle.** A carried-over item is re-presented in full at every sweep until it is answered. An item they must scroll back through an earlier reply to read is as unanswerable as one never shown.

Each item gets the same three-way answer. **Approve** applies it now, **hold** makes no change and carries it forward, **reject** declines it for good. Silence is none of these: an item the person does not mention is not held, because silence proves nothing either way, and an item is only held once they say so.

**Name the write, do not describe the convention.** What they approve is a change to their notes, so the item states which note gains what. An arrow between two slugs will not do, since it leaves the direction to be inferred. **Propose a direction, not a pair**: a keyword tag is one-way by default, so name the note that gains it and say why that direction. The person may answer by redirecting rather than rejecting, which is approval of a narrower write.

Each item carries a stable id, assigned when first queued and kept while it stays undecided: `CV-` for a pair, `MB-` for a membership, `RM-` for a removal, `SL-` for a sourced-link escalation. The list position is renumbered fresh each sweep, so a reply by position is read only against the list it answers.

```
1. `CV-2026-08-29-1`: a-note gets Keyword: another-note. Why it is a genuine
   adjacency, and why in that direction. Recommend approve.
2. `MB-2026-08-31-5`: a-note gets Theme membership: some-theme. Why it belongs.
3. `CV-2026-09-01-3`: Both a-note and another-note get each other as Keyword.
   Why each earns the other in its own right.
```

**An oversized-anchor proposal is presented before the pairs it would absorb**, carrying the anchor, its member count, what the reading of the members found, and the three answers available: mint the missing node, split the overloaded note into its claim plus a bare anchor beside it, or leave it. Where minting is confirmed, the tags it absorbs are listed one per line with the same three-way answer, since each is a removal and a blanket sweep is how a real finding disappears under cover of tidying.

**Removal proposals** come from the decay lane and are marked as removals. Judge them against the promotion test rather than with it: a low similarity says two notes stopped overlapping, not that the tag was wrong, and an unsourced tag claims only that they are worth reading together, which a narrowed claim rarely destroys. Remove where the tag now points at something the note no longer says; keep where the adjacency survives. This is the one place the system takes something away rather than superseding it, and it is available only here.

Approved items are applied with the keyword script rather than hand-edited, where a one-sided tag or a missed stamp slips in. A sourced-link escalation is written by hand, since it carries a citation and is a considered edit. Rejected items go to the dismissal sidecar so they never resurface. Held items are left entirely alone.

**6. Queue a rebuild** for anything the cycle marked stale but could not rebuild alone.

**7. Commit** if the sweep wrote something. A sweep that only presented state and confirmed nothing leaves the tree clean, and then does not commit or push.

## Health check

**Report the harvest state first**, from the generated section at the top of the queue: files processed of total per declared folder, and by how much any folder falls short. It leads because harvest is the one place the derived layer can silently lag the sources, and because the cycle no longer withholds it, a standing backlog is not a held decision but simply work the next cycle still has to run.

Then echo the current scope, so what the system may read stays visible rather than becoming invisible configuration.

Three numbers, as trends rather than snapshots. **Flag rate**, corrections raised per week, the primary quality signal now that there is no endorsement step; rising means synthesis is not trustworthy. **Stale backlog**, the proportion of notes stale; persistently high means either the cadence is wrong or the concepts are badly cut. **Processed but unlinked**, sources producing nothing.

The honest reading matters more than the numbers. Flag rate rising while the backlog consolidates means the system is producing material faster than it produces value, and the correct response is to propose slowing the consolidation or narrowing its scope, not to add machinery. **Flag rate near zero is not automatically good**: it may mean the wiki is accurate, or that nobody is reading it closely enough to notice errors. If usage is low, say so rather than reporting the zero as a success.

## Filter-bubble check

A wiki curated by the person and written by a please-seeking agent entrenches their priors by construction, and fidelity guarantees a faithful mirror rather than an open one. Each sweep, surface and **offer** a `discuss` pass on untested consensus, a standing position or convergence cluster carrying no contradiction and never argued against, and on rubber-stamped synthesis, concepts or links the agent proposed and the person only ever confirmed. The offer is the whole intervention. It never gates, rejects or withholds, and "just tell me" ends it.

## Quarterly

Hub recompilation, deep staleness, and a review of whether the link vocabulary still fits. Not weekly.
