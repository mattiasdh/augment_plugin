# How the plugin is put together

For anyone reading the source, or extending it.

## The four layers

```
augment_plugin/
├── skills/       one verb each; the only thing Claude loads on its own
├── rules/        binds every skill: duties, writing, freshness
├── reference/    the contract, split by subject; loaded per skill, per need
└── scripts/      deterministic; run, never read
```

**Skills are the only auto-loaded layer.** A skill body is what Claude reads when the request matches its description, so it holds the procedure and names the fragments it needs. Everything below it is pulled in deliberately.

**Rules bind regardless of task.** The epistemic duties, the writing rules and the freshness duty apply to every skill, so they are stated once and named rather than copied. A rule copied into two files is a rule that can fall out of step with itself.

**Reference is the contract, split by subject.** The old single file covered twelve subjects in 556 lines and every compiling operation was told to read all of it. Now `process` reads note shape and links; `answer` reads neither. The split is on subject boundaries rather than on length, so a rule sits in one place and is found by what it is about.

**Scripts are pinned implementations, and are run rather than read.** Hash comparison, index compaction, conformance, the relations overlay and the generators are deterministic. A model call that recomputes a hash is waste that can also get it subtly wrong in a way a script cannot, which is why the hasher in particular is pinned: the byte rule is exact, and a convenience reimplementation disagrees on real files and reports staleness that is not there.

Read a script only to debug the script itself.

## What loads when

The cost of a request is the skill plus what it names, not the whole plugin.

| Request | Loads |
|---|---|
| "what do we know about X" | `answer` and the freshness rule |
| "capture this" | `write`, the writing rules, provenance, statuses |
| the nightly cycle | `dream`, all three rules, and four reference fragments |

The cycle legitimately needs most of the set, and that is the honest shape of it: the win is not that everything got smaller but that the light operations stopped paying for the heavy one.

## Why a plugin rather than a skill

The system ran for two months as a single skill whose contract lived inside the vault it governed. That co-location had one real virtue, a vault carried its own rules, and three costs. The method could not be installed anywhere else without copying a vault's internals. Publishing it meant filtering a private archive rather than releasing a repository. And a skill deployed as a zip beside its unpacked source drifts, which needed a checker to detect.

A plugin separates the method from the instance. The vault keeps its content and its declarations; `config.yaml` records which release compiled it, so a mismatch is reported rather than silently compiled over.

## Extending it

**Add a skill rather than a mode** once a skill starts handling two verbs in sequence, or runs past roughly 500 lines. The bound is not aesthetic: a skill body is loaded whole, so a file handling four verbs makes every request pay for three it does not need.

**Add a reference fragment rather than a section** once a rule does not belong to any existing subject. Fragments are named by subject so they can be found by what they are about.

**Prefer a check to a rule.** A rule with no enforcement holds until someone is busy, which is exactly when it is needed. Where a fix can be made structural, make it structural; where it cannot, put the rule on the surface actually read at the moment it binds, rather than adding weight to a statement already being missed.

**Rules come from real failures, and stay phrased as rules.** The system keeps no separate incident record: a rule that needs its case history to be understood has been written badly, and a case history nobody reads at runtime is a file every pass pays to skip. Where a rule looks arbitrary without its reason, the reason is half a sentence inside the rule.
