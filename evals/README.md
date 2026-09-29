# Evals

`routing/` checks that a request reaches the skill meant for it. The skills are chosen by their descriptions alone, and the memory/content boundary is where a misroute does harm: a client's requirement filed as memory, a tool quirk filed as a source note. Each case is a request phrased the way a person would type it, never a copy of the trigger words, graded on which skill Claude loads; boundary cases also assert that the neighbouring skill did not fire.

Each case scaffolds a minimal vault (`scaffold.sh`), so the session-start hook reports Tier 1 and the choice of skill is what gets tested. A system-prompt line stops the run once the skill is loaded, which keeps a run to a few cents.

```bash
claude plugin eval . --ablation none --tag routing --scaffold -j 4
claude plugin eval . --ablation none --tag routing --scaffold -j 4 --model haiku   # the margin check
```

`--ablation none` skips the no-plugin baseline, which cannot route to a plugin skill at all. Run the suite after any change to a skill's `description:`. A full run costs roughly 3 USD at list price, the Haiku run about 2.

The prompts are generic on purpose: this repository is public, so no client or project names.
