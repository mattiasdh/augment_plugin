# Skills kept in the vault: method that reads its rules live

## The principle

**A skill is method; the rules it applies are the person's, and live where the person can see and change them.** A brand voice, a channel convention, a partner register or a checklist would matter to a colleague doing the work without Claude, so they are not memory. They are also not knowledge for the wiki: they are instructions, read on every use. They therefore get their own place in the vault, beside the skill that reads them, out of the wiki's scope and under the person's approval.

What goes wrong without it is drift. A skill uploaded to claude.ai cannot be edited from a conversation, so feedback lands wherever a tool allows a write: a memory card, a note, a Project file. The rules then exist in several copies that disagree.

## The place

`config.yaml` declares one root, and the root is ruled out of scope like any method folder, so nothing in it is compiled:

```yaml
skills:
  root: notes/30_ASSETS/skills
```

One folder per skill, named as its SKILL.md names it:

```
<root>/<skill>/
  SKILL.md        the thin skill: workflow, checks, and where its references live
  references/     the rules, read live on every use; they evolve with the person's feedback
  CHANGELOG.md    one dated line per approved rule change
  dist/<skill>.skill   the upload package, built by package_skill.py, never edited
  _archive/       superseded versions kept for the record; never packaged
  README.md       optional; a third-party skill says so here and is not edited
```

A folder carrying `.claude-plugin/` is a plugin's review copy, not a skill, and the checks pass over it.

## Reading the references

The thin SKILL.md names its reference files and where to read them:
- **With the vault on disk** (Code, Cowork): the file at `<root>/<skill>/references/<file>`.
- **Through the connector** (Chat, web, mobile): `vault_read` on the same path. The connector allows the declared root even though it is out of scope.
- **With neither**: the copies bundled in the package, which carry a stamp line naming the last approved change and a content hash, and the skill says once that it read a snapshot.

## Changing a rule

Feedback that changes a rule is proposed as the exact lines to add, change or remove in the reference file, and applied only on the person's approval.
- **With the vault on disk**: apply the edit, add the dated line to CHANGELOG.md, run `package_skill.py <vault> <skill>`, and tell the person to upload the new package.
- **Away from a filesystem**: park it with `memory_offer` (or `memory_write.py offer`), kind `correction`, target the reference file. The sweep applies it with the person.
- **Never as a memory card.** Only Claude's own recurring slips in running a skill are memory, as a card scoped to the skill's name.

## Checks

`package_skill.py <vault> --check`, also run inside `conformance.py`, reports as advisories:
- a folder with no SKILL.md at its top;
- frontmatter that is not valid YAML or lacks a name or description;
- a skill named otherwise than its folder;
- a `references/` file the SKILL.md names that does not exist;
- a `dist/` package behind its live files.

None of these fails a build, because the skills are not part of the wiki. The packaging is deterministic: entries sorted and timestamps fixed, so an unchanged folder rebuilds byte for byte and is never rewritten.
