# Running the cycle unattended

The nightly cycle runs as a **cloud routine** against the vault's private git repository. Product details change, so verify against the current routines documentation before relying on this file. What follows is the rationale, why the routine is shaped this way.

## Why cloud rather than a desktop task

A desktop task fires only while the app is open and the machine awake, which rules it out for a nightly cycle. A cloud routine runs on managed infrastructure regardless of local state. The trade is that it has no local files: it works from a fresh clone of the default branch, so **everything the cycle needs must be committed**, the sources, the wiki, the index and the history. The method itself comes from the installed plugin rather than the repository, which is one thing that got simpler in the move.

## The accumulation problem

Every run starts from a fresh clone of the default branch, and by default a routine may push only to prefixed branches. Together these trap the cycle: if each night's output lands on an unmerged branch, the next night clones the default branch, never sees it, and repeats the work, so the index never accumulates and near-duplicates multiply.

**The fix is to push directly to the default branch**, so each run builds on the last. That is safe here for reasons specific to this system rather than general ones: the cycle never writes to a source, the wiki is derived and rebuildable, the index is derivable from history, and git makes every run reversible, so a review gate would only be guarding regenerable output.

Push **after each successful batch**, once its writes, conformance pass and index compaction have all succeeded, so every pushed state is internally consistent and an interruption costs at most the last batch. Set branch protection on anything that must not be touched; the routine's branch setting and the host's rules are independent layers, and the second is the stronger.

## Sync: git or a desktop client, not both

The routine pushes and the local machine pulls to see the result. If the same folder is also synchronised by a desktop client, two mechanisms are writing to it and one does not understand the other. **A `.git` directory inside a cloud-synced folder is a well-known source of repository corruption**, because git operations are multi-file transactions a syncer can capture half-finished. Use git as the vault's sync path and take it out of the desktop client, or at minimum exclude `.git`.

## Exclusion is not access control

A routine clones the whole repository. `#excluded` stops a source being **processed**; it does not stop it being **cloned** onto cloud infrastructure. For material that must not leave the local machine, tagging is the wrong instrument: put it in a separate repository, or exclude it from the tracked one, and decide this deliberately per folder rather than discovering it later.

## Identity

A routine commits through the linked identity, so its commits are indistinguishable by author from work done by hand. That is why every commit the cycle makes carries the `Assisted-by:` trailer and never `Co-authored-by:`. The trailer is the only thing in the commit marking an overnight machine pass.

## Model, limits and permissions

Pick a strong model, since the cycle's whole value is judgement, and push the mechanical phases into scripts as the skill directs. Runs count against a daily allowance that varies by plan; one nightly run leaves room for manual ones. **Routines run with no permission prompts**, which removes a desktop task's stall risk but also its safety net, so what a run can reach is set entirely by the repositories, branch-push setting, network configuration and connectors selected. Include only what a self-contained vault needs, and likely no connectors at all.

## The routine prompt

Keep it short, and let it invoke the skill rather than restate it, so changing how the cycle behaves means releasing the plugin rather than editing the routine.

```
Run /augment:dream over this repository.
Stop at roughly 90 percent of session budget and checkpoint cleanly.
Commit with an Assisted-by: trailer. Never Co-authored-by:.
Anchor, converge and mint as phase 6 directs, applying through
apply_keywords.py --auto --run <run-id> --reason so every write is recorded.
Report to the queue, listing each autonomous write on its own line.
Do not act on anything the skill marks as queued: a removal, a split, a
supersession, a tension, or anything in the source layer.
```
