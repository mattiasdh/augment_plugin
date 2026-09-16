# Note shape

## Frontmatter

**Wiki-note metadata is YAML frontmatter**, in the key order `type`, `kind`, `status`, `generated`, `sources`, `further_sources`, `keywords`: identity, then lifecycle, then provenance, then navigation. A `kind: person` entity carries one further optional identity key, `public_figure: true`, between `kind` and `status`. The body below the fence is uninterrupted prose, beginning at the title.

```markdown
---
type: "[[concept]]"
kind: "[[claim]]"
status: "#current"
generated:
  by: augment/claude-code
  at: 2026-07-22 09:14
sources: ["[[12.04 source-note]]", "[[12.09 design-review]]"]
further_sources: "[[sources#12 tender]]"
keywords: ["[[thermal-mass-lightweight-construction]]", "[[hygrothermal-comfort]]"]
---
# Bio-based insulation buffers moisture as well as heat

Body prose, every sentence traceable to a cited source.
```

**`sources` is the note's citation list**, the material it was compiled from, and it is what the every-note-cites-a-source rule is checked against. `further_sources` is a single stable back-link into the sources view, carried by project entities. Both are metadata carrying no prose, because a list of wikilinks in a field is the shape a link index resolves.

`type` and `kind` stay wikilinks so they remain clickable and resolve to hub notes. `keywords` stays a list of wikilinks so each one is a real graph edge producing a backlink, and those backlinks are what the theme bodies and the membership harvest are computed from. **This is why keywords are not folded into tags**: a tag is a label in a flat namespace with no note behind it and no backlink, whereas a keyword points at a note that exists and is existence-checked like any other link.

**Quote the wikilinks.** A bare `[[x]]` in YAML parses as a nested sequence, so links are written `"[[x]]"`. The generators emit them quoted and one shared reader parses them, rather than a regex per script.

`keywords` is optional and omitted when empty. It is the note's lightweight navigational layer, distinct from the sourced links block.

**`generated.at` carries `YYYY-MM-DD HH:MM` in the writing machine's local time.** It means when this note's content last moved. A note can be written several times in one day, and a date alone cannot order those writes or show that a note was touched after the run that read it. Local rather than UTC, because the person reads these stamps against their own day and a source written by hand is stamped in local time by whatever tooling writes it. The offset is not recorded. Build provenance, which sources a note was compiled from and at which hashes, stays in the index rather than the note: it is machine state, it changes on every rebuild, and it would clutter the page without telling a reader anything they came for.

## Source notes keep their own shape

The system writes three keys into a source's frontmatter and nothing else, alongside whatever the person's own tooling writes there. The source layer is the person's, and rewriting their notes to a convention that serves the derived layer would be backwards. Their fields are read, never written or reordered.

The state tag is **`augment:`**, and the name is doing work: a vault-written `status:` would collide with a field that already means something in the person's own vocabulary, so each layer keeps its own word for its own state. The value is quoted, because a bare `#` opens a YAML comment and the tag would parse as null.

```yaml
---
augment: "#processed #linked"
created: 2026-08-13 11:12
updated: 2026-08-13 11:12
---
```

`created:` is written once, when the note is first made, and never again; `updated:` on every edit, so `created:` can never postdate it. Neither is backfilled onto notes predating the convention, since a git first-commit date records when a file entered the repository rather than when it was written, and a wrong `created:` is worse than none.

## Body shape, by type

Fixed here rather than in templates a writer fills in, because a second copy of a shape disagrees with the first sooner or later.

| Type | Body |
|---|---|
| `concept` | H1, prose, `## Links` |
| `concept` of kind `procedure` | H1, a `Goal:` line and an optional `Preconditions:` line, brief prose, `## Steps` as an ordered list, `## Links` |
| `entity` | H1, prose, `## Role in the archive`, `## Links`, and on a project entity `## Decisions` |
| `tension` | H1 naming the conflict, `## Position A: [[note]]`, `## Position B: [[note]]`, `## Boundary conditions`, `## What would settle it` |
| `theme`, `hub`, view | generated wholesale by a script; no hand-written body |

The H1 restates the note's claim in ten words or fewer and is the only heading above the blocks named here. **`## Role in the archive`** answers why the entity appears at all, what it originates, owns, locates or governs, and it is what makes an entity note worth keeping rather than an encyclopaedia stub. A **tension**'s two positions each carry their citation and are each stated at their strongest, since the note exists to hold a conflict open rather than settle it; "irreducible" is a legitimate answer under what would settle it.

A **source note** is the person's. Where the model drafts one, it ends with any citekey definitions at the foot, `[#Citekey]: Author (Year): *Title*, page.` A **correction note** is a source note of `kind: correction` whose body answers three questions in order: what the process concluded, what is actually the case, and on what basis. It cites the wiki note it corrects.

## Kind vocabulary

For entities: `person`, `place`, `organisation`, `product`, `tool`, `project`. For concepts: `principle`, `method`, `model`, `metric`, `standard`, `claim`, `procedure`. Both are open to extension by a documented decision, the way `project` was added. Every concept and entity carries exactly one kind, for symmetry and so the kind hubs are complete. Tension and hub notes carry no kind, so there are no kind sub-hubs beneath the tension type-hub.

A `procedure` concept records executable know-how, an ordered tool-bound sequence, as distinct from a `method`, which states a general approach independent of any particular tool. A method says what to do and why it applies; a procedure says how, in order. A procedure carries a steps block alongside its prose, each step traceable to a cited source like any other sentence. This is the natural home for how-to material whose concept yield is otherwise low.

**`public_figure: true`** is optional on a `kind: person` entity. Kind alone does not say whether the entity is a cited author, safe to name if the system is ever published, or a confidential direct contact named only inside a project log, and the publish guard has to treat one as a leak and the other as ordinary prose. The key defaults to absent, which reads as **not public**, the protective default. It is set only on the deliberate finding that the sources establish the person as a public author, speaker or figure, cited from a book, essay or lecture rather than named as a party to the practice's own work.

## Open Knowledge Format

The frontmatter is a minimal implementation of OKF 0.2, with three deviations stated once so they are not re-argued field by field.

**`sources` is a flat list of wikilinks**, not OKF's list of objects. The object shape invites build provenance into the note, which this contract keeps in the index deliberately, and a flat field of wikilinks is the shape a link index resolves. A wikilink is a path descriptor, so the required `resource` is present, and the deviation is in form rather than substance.

**`generated.at` carries the last meaningful content change** in local time without an offset, rather than an ISO 8601 instant, because the vault has one author in one place and every check that reads the stamp compares dates.

**`status` keeps this system's five values** rather than OKF's three. The vocabulary is shared with the index and the queue, and it distinguishes states OKF's cannot: a note whose sources moved is not a draft, and a note under dispute is neither. For an OKF consumer the mapping is `#current` to stable, `#superseded` to deprecated, and the rest to draft.

Three optional families are declined rather than deviated from. A `verified` field would record an independent verification event, which the sweep performs but which is not worth recording on the note. `stale_after` would date staleness, where this system derives it from source content hashes, which is stronger, and a second staleness authority would only disagree with the first. `title` and `description` would duplicate the H1 and the index title, and a second copy drifts.
