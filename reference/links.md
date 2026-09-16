# Links and the relationship ladder

**One ladder decides every relationship, evaluated top-down for each candidate pair.** The rungs are ordered by the strength of what the relation asserts, not by which relation happened to be written first. A candidate stops at the first rung that fits, and what it becomes is what that rung writes.

| Rung | Test | What it writes |
|---|---|---|
| **1. Sourced** | a source states a specific relationship between the two notes | a sourced `## Links` entry, with its reason and citation |
| **2. Anchored** | both notes belong to a cluster that has, or deserves, an anchor | one keyword tag per note **onto the anchor**, and the anchor minted where none exists |
| **3. Adjacent** | a specific direct adjacency neither rung above already carries | a one-way keyword tag between the two |
| **4. Neither** | none of the above | a dismissal to the sidecar |

**Rung 2 sits above rung 3 on arithmetic rather than taste.** A cluster of *n* notes around a common centre generates *n(n-1)/2* pairwise candidates and needs *n* membership tags, so proposing the pairs means judging a quadratic where a linear answer exists, and the person answers the same question repeatedly instead of once.

## Anchors

**The anchor a cluster deserves is often an ordinary note, not a theme.** A theme is right only where the cluster gathers around a bare topic that asserts nothing. Where it gathers around something that does assert, the missing node is a concept or entity of whatever kind fits, and it is minted the way any of those is, from the sources that establish it. A theme is the one node mintable without a source; everything else on this rung obeys the ordinary rule, and where no source establishes the concept, nothing is minted and the cluster keeps its bare anchor.

**An oversized anchor is how a missing node announces itself.** An anchor grown past roughly seven members **and** whose members hang together rather than merely sharing a topic is the signal: the notes are gathering around something nobody has written, or around a content note quietly doing double duty as a claim and as a gathering point. **Size alone does not say this.** A project entity gathers notes with nothing to do with each other and stays sparse; a real cluster is dense, and the density the vault's own themes sit at is what fixes the floor. The relations script computes both numbers and reports the anchor at the moment the membership lane proposes to grow it again, which is when the question is worth asking. Three answers are available: mint the missing concept, split an overloaded note into its claim plus a bare anchor beside it, or leave it, which is honest whenever the anchor genuinely is what its members are about.

**Promotion absorbs a tag only where absorption is lossless.** When a cluster gains an anchor, the pairwise tags that said no more than "both of these are about the same thing" are replaced by membership tags, since the anchor now carries that. A tag saying something the anchor does not carry survives, which is exactly what rung 3 exists for, and a blanket replacement would quietly delete real findings under cover of tidying. Absorption is judged per tag, defaulting to absorb, and each removal is confirmed at the sweep.

## When a candidate is suppressed

**A candidate is suppressed only where an existing relation carries the same claim, which is not the same as a path already existing.** Any two notes in a small dense archive are joined by some path; treating that as disqualifying lets whichever relation was written first suppress a stronger direct tie, and makes the graph depend on processing order rather than on what the sources say. Three carriers subsume, each for a stated reason rather than by precedence.

**Authorship.** A `kind: person` entity and a note joined through the person's own work. The person note exists to name an author, their model does the connecting, and a tag from the note to the author reaches a place the graph already reaches. This holds however well-connected that model is.

**Specificity.** A carrier joining few notes says something specific about the ones it joins and stands in for the pair. A carrier joining many says only that both notes sit in a broad topic and stands in for nothing, so a strong pair sharing only a broad anchor still competes. The script fixes where that line falls, because it is a tuned number.

**Small shared anchor.** Two notes tagged to the same keyword anchor of four or fewer members. This is a narrower count than specificity: it counts only inbound anchor membership, not the anchor's own outward ties or any sourced links, so a well-connected small anchor can clear the specificity cap and still be caught here. A small anchor is close to redundant with the tag itself, since almost nothing else is gathered there to distinguish the pair.

## Tier 1, sourced links

**Three types, no others: `related`, `example_of`, `contradicts`.** Each states that a source establishes a relationship between two notes, so each is a claim carrying its reason and the source that reason derives from. `related` is the general case and carries the specifics in its reason line. `example_of` is kept apart because instance-of is directional in a way `related` is not. `contradicts` is kept apart because it is machine-read, feeding the divergent lane and conflict-as-research.

Three types is what the writing actually distinguishes, and a type nobody draws costs a judgement on every link that does not need it. Where a narrower word is worth keeping, it goes at the head of the reason line rather than becoming a fourth type.

```markdown
## Links
- related [[thermal-mass-lightweight-construction]]
  Why: refines it. The buffering effect is what makes the thermal argument hold in
  timber frame, where mass alone does not.
  Source: [[12.04 selection-criteria]]
```

**The citation line is not decoration. A sourced link with no source is a defect**, because it is a claim the model composed rather than read.

## Tier 2, keywords

The lightweight navigational layer: a frontmatter list of wikilinks, no reason and no source.

```yaml
keywords: ["[[whole-life-carbon]]", "[[fit-out-churn]]", "[[carbon]]"]
```

**A keyword tag is directional, and one-way by default.** A tag on note A says A is worth reading beside B; it does not require the reverse on B, because the backlink already carries the path back and writing both duplicates in frontmatter what the graph holds anyway. Most confirmed adjacencies are genuinely asymmetric: a project is worth tagging with the method it applies, while the method is not worth tagging with every project that ever applied it, and a note accumulating the reverse of every tag pointing at it becomes a list of everything rather than a note. The symmetric case is real but the exception, written only where each note earns the other in its own right. A theme is never back-tagged at all, its body being generated from the back-references.

A keyword asserts nothing beyond adjacency, which is exactly what the relations overlay computes. Because it makes no factual claim it needs no source, and that is not a fidelity hole, since there is nothing to source. It is **exempt from the source rule** governing tier 1.

Its targets are the content layer only: concept, entity, theme and tension notes. **It must never point at a hub**, since tagging a note with "the claim hub" is meaningless. Each target is existence-checked like any link. Keywords are populated by the convergence pass and the sweep, never by composing a plausible adjacency.

**The two tiers are kept as distinct names so they never collide.** A source-established relationship is a sourced links entry; a model-noticed, unsourced adjacency is a keyword tag. The overlay proposes the latter cheaply; only a source puts a connection in the former. There is no migration between them.

## Isolation is not a defect

**Wiki notes do not need to link to each other.** A concept note always cites at least one source, so it is connected by construction. Isolated notes are normal and are not a finding. Connections may emerge as the archive grows, or may not. The only genuine defect is a wiki note citing no source at all.
