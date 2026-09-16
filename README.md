# augment

A Claude Code plugin for running an **intelligence-augmentation vault**: a tree of notes you wrote, plus a wiki of concept, entity, theme and tension notes the model compiles from them and maintains on its own.

It is not a Zettelkasten tool and not an automation. The division of labour is fixed: you write the sources and decide what is worth reading; the model writes and maintains every wiki note, cross-references them, detects contradictions and drift, and reports what needs your judgement. You never edit a wiki note, because it is compiled output and the next build would overwrite it. Corrections travel through the sources.

## What it gives you

Seven skills plus a dispatcher, each one verb.

| Skill | What it does |
|---|---|
| `/augment:wiki` | Routes a request, and carries the rules that bind every other skill |
| `/augment:write` | Writes into your own layer: capture a source, comment on one, file a correction |
| `/augment:process` | Compiles sources into wiki notes, rebuilds what went stale, harvests project decisions |
| `/augment:answer` | Retrieves notes, or synthesises an answer that closes with what the vault does not know |
| `/augment:discuss` | Thinks a question through against the vault, and argues back |
| `/augment:mint` | Generates one node you name and wires it into the graph |
| `/augment:dream` | The nightly cycle: detect, rebuild, consolidate, check, connect, regenerate, report |
| `/augment:verify` | The weekly sweep: audit what the cycle wrote, decide what it may not decide alone |

Most of the time you do not type these. The skills carry trigger phrases, so asking what the archive knows about something reaches `answer` on its own.

## Install

```bash
claude plugin marketplace add mattiasdh/augment_plugin
claude plugin install augment@augment-plugin
```

For local development, point the marketplace at a checkout instead:

```bash
claude plugin marketplace add ./augment_plugin
```

To declare it for a project rather than per user, put it in that project's `.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "augment-plugin": { "source": { "source": "github", "repo": "mattiasdh/augment_plugin" } }
  },
  "enabledPlugins": { "augment@augment-plugin": true }
}
```

The plugin ships two `UserPromptSubmit` hooks, one checking that your working copy is not behind the remote and one re-asserting the writing register on a prose-shaped prompt. **Both exit silently outside a vault**, so the plugin sits quietly alongside other plugins in projects that have no wiki.

## What a vault looks like

```
your-vault/
├── notes/              your own notes, in whatever scheme you use
│   └── _inbox/         unaddressed, triaged or discarded
└── augment_wiki/
    ├── config.yaml     the one file you edit: language, author, scope, harvest
    ├── index.jsonl     current state, one entry per note or source
    ├── history.jsonl   append-only, every entry ever written
    ├── concept/  entity/  theme/  tension/
    └── hub/  view/     generated indexes and cross-cutting views
```

The method lives here in the plugin and is versioned separately, so a vault carries its content and its declarations and nothing about how the system behaves. `config.yaml` records which release last compiled it.

## Starting from an existing archive

Point it at a tree you already have. **Nothing is processed until you say so.** The first cycle reports how many sources await declaration rather than sweeping them in, because in an archive holding client or confidential work, deciding on your behalf is the dangerous error. You declare whole folders at a time during the sweep, and a folder nobody has ruled on stays visibly undecided rather than being quietly treated as excluded.

## How it is built

Each skill loads only the rules and reference fragments it needs, so a read-only question does not pay for the compiler's contract.

- `rules/` binds every skill: the epistemic duties, the writing rules, the freshness duty.
- `reference/` is the contract, split by subject: layout, note shape, statuses, provenance, links, scope and the ledger, hubs and views.
- `scripts/` is deterministic and is run, never read. Hash comparison, index compaction, conformance, the relations overlay and the generators are all code, because a model that recomputes a hash is waste that can also get it subtly wrong.
- `schema/` types the ledger, so a line of `index.jsonl` or `history.jsonl` can be validated rather than trusted.

## Licence

MIT. See `LICENSE`.
