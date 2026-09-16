#!/usr/bin/env python3
"""What the plugin publishes, and what must never appear inside it.

The plugin is a public repository and the vault it governs is private, so every
file under the plugin tree is published the moment that repository is pushed.
This module names that surface once and `conformance.py` guards it, so the check
cannot drift from what actually ships.

The real risk is not the vault leaking wholesale; it is the examples. The rules
and reference fragments carry worked examples, and this archive's examples come
from real clients and projects. The denylist of terms is therefore derived at
run time from `index.jsonl` and `config.yaml`, and is itself never published,
because a hand-written list of a practice's clients is the thing it exists to
protect.
"""
import json, os, re

# What ships when the plugin repository is pushed, relative to the vault root
# while the plugin still lives inside it. Once it is split out, the whole
# repository is this list and the guard runs over all of it.
MANIFEST = [
    "augment_plugin/",
]

# Never published, even though they sit inside a MANIFEST directory.
EXCLUDE = [
    "__pycache__/",
    ".pyc",
    ".git/",
]

# Generic words that legitimately appear in system prose and happen to also sit
# inside an entity name. Kept here rather than in the derived list because these
# are properties of English and of the domain, not of this vault.
ALLOW = {
    "building", "buildings", "office", "offices", "renovation", "feasibility",
    "portfolio", "strategy", "service", "centre", "center", "redevelopment",
    "offshore", "project", "projects", "follow", "asset", "reuse", "design",
    "study", "note", "notes", "plan", "material", "materials", "system",
    "standard", "report", "carbon", "energy", "circular", "wonen", "nest",
    "library", "assets", "comm", "system", "candidatures", "vision",
    # The system's own name, and the words of its own directory names. These reach the
    # derived list through the scope-rule loop below, which tokenises a rule's path: a
    # rule on a structural folder (`augment_plugin`, `augment_wiki`) splits on the
    # underscore and puts the product's own name into the denylist, after which every
    # published file mentioning it reads as a leak. A product name is structurally
    # incapable of being a client identity here, so it is excluded permanently rather
    # than per folder.
    "augment", "plugin", "wiki", "notes",
}


def leak_terms(index_entries, config=None):
    """Distinctive client and project tokens, derived from the vault's own data.

    The identities worth protecting are already modelled: a client is an
    `organisation` entity and a job is a `project` entity, and the folders they
    live in are named in `config.yaml`'s scope rules. Deriving the list from those means it
    never needs hand-maintaining and never goes stale as work is won or filed.

    A `kind: person` entity is excluded when its index entry carries
    `public_figure: true` (CONTRACT §4, §11): a cited author is not a client or a
    confidential contact, and belongs on the page rather than in the denylist a
    fork's illustrative prose gets checked against. The key defaults to absent,
    which stays in the denylist, the protective default for a direct contact.
    """
    terms = set()

    def add(text):
        for tok in re.findall(r"[A-Za-z][A-Za-z0-9.-]{3,}", text or ""):
            t = tok.strip(".-")
            if len(t) >= 4 and t.lower() not in ALLOW:
                terms.add(t.lower())

    for e in index_entries:
        if e.get("type") == "entity" and e.get("kind") in (
                "project", "organisation", "person", "place"):
            if e.get("kind") == "person" and e.get("public_figure"):
                continue
            add(e.get("title", ""))
            add(os.path.basename(str(e.get("id", "")))[:-3].replace("-", " "))
    for r in ((config or {}).get("scope") or {}).get("rules", []):
        add(str(r.get("path", "")).replace("/", " "))
    return terms


def published_files(root):
    """Every file the manifest would ship, as vault-relative paths."""
    out = []
    for m in MANIFEST:
        full = os.path.join(root, m)
        if m.endswith("/"):
            for dirpath, _, names in os.walk(full):
                for n in names:
                    p = os.path.relpath(os.path.join(dirpath, n), root)
                    if not any(x in p for x in EXCLUDE):
                        out.append(p)
        elif os.path.exists(full) and not any(x in m for x in EXCLUDE):
            out.append(m)
    return sorted(out)
