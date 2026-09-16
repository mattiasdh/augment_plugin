# Layout and note types

## The central principle

**The wiki is derived from the sources. It reflects what the sources say.**

The source tree, a structured scheme such as Johnny Decimal or PARA, holds the person's own notes, written over years in their own words. The wiki is a lookup layer built over it, written and maintained entirely by the model.

The obligation is **fidelity, not truth**. A source can be mistaken, out of date, or contradicted by better evidence, and the wiki must still represent what it says. The wiki is a faithful account of the archive, not of the world.

An apparent error in a source is therefore never corrected in the wiki. It is recorded as an observation and reported at the sweep, where the person decides whether to write a correction. Silently improving a source while compiling it produces a wiki that contradicts the material it cites, and destroys the one property that makes the layer trustworthy.

Three consequences. The person does not write or edit wiki notes, since a hand edit is destroyed by the next build. Corrections go to the source layer. And every wiki note must be reproducible from the sources it cites, so a sentence that cannot be traced to a source does not belong in it.

## The tree

```
VAULT/
├── notes/                    SOURCES, the person's own structured tree
│   ├── _inbox/               fleeting, no address, triaged or discarded
│   └── 10-19 … /             Johnny Decimal, PARA, or whatever scheme the person uses
│       └── 12 tender/
│           ├── 12.01 site-visit.md
│           └── 12.04 selection-criteria.md
└── augment_wiki/             the augment layer, written by the model
    ├── config.yaml           the person's declarations: language, author, scope, harvest
    ├── index.jsonl           current state, one entry per note or source
    ├── history.jsonl         append-only log of every entry ever written
    ├── verify-queue.md       the report the sweep reads
    ├── relations_dismissed.jsonl
    ├── concept/              ideas, principles, methods, claims
    ├── entity/               people, organisations, places, products, tools, projects
    ├── theme/                topical anchors a cluster points at through keywords
    ├── tension/              recorded conflicts
    ├── hub/                  generated indexes: one per type, one per kind, plus hub.md
    └── view/                 generated cross-cutting views: relations, timeline, sources
```

**The method is not in the vault.** Rules, skills, reference and scripts ship in the plugin, versioned and released separately, so a vault carries its content and its declarations and nothing about how the system behaves. `config.yaml` records which plugin version compiled it.

**Subfolders are by type, never by topic.** A concept belongs to many topics and must not be forced to pick one. A concept is unambiguously a concept, so type folders cost nothing and give a browsable overview that a flat directory of several hundred notes cannot. Obsidian resolves wikilinks by filename regardless of folder, so links are unaffected by where a note sits.

Two rules bind the tree.

**Links only flow upward.** Wiki notes cite sources; sources never link out to the wiki. Stated explicitly because the model over-links otherwise.

**The address is a commitment.** The model files to `_inbox/`; the person assigns the address in whatever scheme the tree uses.

## Note types

**Every wiki note declares exactly one type, and the type decides its folder, its body shape and the test it must pass.** A note whose type and folder disagree is a defect rather than a preference. The one documented exception is the `hub` type, whose views live in their own folder while carrying the same type, since what sets a view apart is what it draws rather than a separate type.

| Type | Folder | Holds |
|---|---|---|
| `concept` | `concept/` | ideas, principles, methods, claims |
| `entity` | `entity/` | people, organisations, places, products, tools, projects |
| `theme` | `theme/` | topical anchors, a named gathering-point for a cluster |
| `tension` | `tension/` | recorded conflicts |
| `hub` | `hub/`, views in `view/` | generated index notes, one per type and kind, plus the views |

A **theme** is first-class but unusual: an anchor, not a claim. Where a concept is compiled from sources and asserts something, a theme names a recurring topic that many notes point at through their keywords, and its body is the generated list of notes reaching for it. It carries no kind and **cites no source**, because it asserts nothing beyond "these notes gather here". It differs from a hub in being curated into existence rather than automatic. **A theme a source actually frames does not stay a theme**: that framing is a sourced concept note, and the theme, if kept, remains the bare anchor beside it. Mint one when several notes already reach for a topic and none anchors it; two or three notes sharing a topic simply list each other and need no theme.

A **concept** note is not restricted to a claim. Frugality, shearing layers of change and a specific claim about moisture buffering are all concepts, because all three answer the same question: what the idea is and how it works.

An **entity** note records a person, place, organisation, product, tool or project that the archive establishes. A **project** is a first-class entity kind, because a design project is an endeavour with a client, site, programme, team and status rather than a mere place. It earns its note by what the sources establish and what it connects, never by operational minutiae: routine dated logs are not processed into it as concepts, while description, vision and feasibility files are. A project entity may carry a decisions block, a dated and sourced list harvested from those logs, which is what lets the timeline view draw a chronology without a note per decision.

**Every note must earn its place, and the test differs by type.** For a concept: what is it, and by what mechanism does it work? For an entity: what role does it play in this archive, and what does it connect? A note answering neither is a label rather than a note, and must not be written.

**An entity note is not an encyclopaedia entry.** It records what the archive establishes and why the entity appears at all. Biography drawn from general knowledge rather than a cited source is a fidelity breach, not helpfulness.
