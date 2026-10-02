# Evals

`routing/` checks that a request reaches the skill meant for it. The skills are chosen by their descriptions alone, and the memory/content boundary is where a misroute does harm: a client's requirement filed as memory, a tool quirk filed as a source note. Each case is a request phrased the way a person would type it, never a copy of the trigger words, graded on which skill Claude loads; boundary cases also assert that the neighbouring skill did not fire.

Each case scaffolds a minimal vault (`scaffold.sh`), so the session-start hook reports Tier 1 and the choice of skill is what gets tested. A system-prompt line stops the run once the skill is loaded, which keeps a run to a few cents.

```bash
claude plugin eval . --ablation none --tag routing --scaffold -j 4
claude plugin eval . --ablation none --tag routing --scaffold -j 4 --model haiku   # the margin check
```

`--ablation none` skips the no-plugin baseline, which cannot route to a plugin skill at all. Run the suite after any change to a skill's `description:`. A full run costs roughly 3 USD at list price, the Haiku run about 2.

The prompts are generic on purpose: this repository is public, so no client or project names.

## Results on record

- **2026-09-29, before the description changes**: default model 41/41; Haiku 23/41, confusing the weekly sweep with the nightly cycle, digesting sources with the cycle, recall with answer, and a client's drawing convention with the person's own.
- **After sharpening eight descriptions**: default model 41/41; Haiku 26/41. The sweep and cycle confusions are gone. The weak boundary left is `write` against `remember` on Haiku, which tends to read "note this down" as memory; a trace showed it reaching first for Claude Code's built-in auto memory. Treat a Haiku score as a margin indicator, and the default model's as the gate.

2026-10-02: 44 cases, adding three "keep this" requests (content to `write`, method to `remember`, a rule for a skill's output to `write`). Default model 44/44, after `write`'s description took the skill-rule case, which the first run sent to `remember` (43/44).
