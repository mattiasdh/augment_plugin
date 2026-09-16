"""Shared helpers for the augment generators. Run, never read (CONTRACT §9)."""
import datetime, os, re, yaml

FM = re.compile(r"\A---\n(.*?)\n---\n?", re.S)


def load_config(root):
    """The vault's hand-written settings, `augment_wiki/config.yaml` (CONTRACT §9).

    House language, source contexts, scope rules and the harvest declaration: the
    things the person declares and the system obeys, as against the index, which is
    machine state projected from the ledger. Keeping them in the index meant the one
    file nobody may hand-edit was also the only place to change what the system may
    read, and it meant a scope rule set was a single three-thousand-character line
    that git could only diff whole.

    Missing or empty reads as `{}`, and every caller defaults from there, so a vault
    that has declared nothing yet fails closed rather than erroring: no scope rule
    means no folder is in scope, which is what CONTRACT §9 already requires of a
    folder with no rule.
    """
    p = os.path.join(root, "augment_wiki/config.yaml")
    if not os.path.exists(p):
        return {}
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def display_path(path, config):
    """A source path with the vault's source root stripped, for display.

    Sources live under one folder (`notes/` by default) so the wiki, the plugin and
    the person's own tree sit side by side. That prefix is on every source id, which
    makes it noise in any grouping or heading, and worse than noise in a heading:
    `sources.md` headings double as link anchors that notes point at with
    `further_sources:`, so a prefix appearing in one renames every context at once
    and breaks every pointer. Stripping it here keeps the anchors as they were.

    A vault that declares no `source_root`, or whose sources sit at the vault root,
    gets the path back unchanged.
    """
    root = str(config.get("source_root") or "").strip("/")
    if root and (path == root or path.startswith(root + "/")):
        return path[len(root) + 1:]
    return path


def scope_of(path, config):
    """Where a path stands against the scope rules: one of `ignore`, `in`, `out`,
    `undecided` (CONTRACT §9).

    Three states, not two, and the third is the point. CONTRACT §5 argues at length
    that for a *source* the absence of a decision is not a decision, since sweeping
    in unconsidered material and recording "not yet asked" as "deliberately
    excluded" are both wrong. The same holds a level up: a folder nobody has ruled
    on has to stay distinguishable from one ruled out, or a folder added today reads
    exactly like one passed over for months and never gets asked about.

    Precedence is longest path first, so a subfolder may include or exclude against
    its parent. `ignore` wins outright: those are not knowledge at all.
    """
    sc = (config or {}).get("scope") or {}
    for ig in sc.get("ignore", []):
        if path == ig or path.startswith(ig.rstrip("/") + "/"):
            return "ignore"
    best = None
    for r in sc.get("rules", []):
        d = str(r.get("path", ""))
        if (path == d or path.startswith(d + "/")) and (
                best is None or len(d) > len(str(best.get("path", "")))):
            best = r
    if best is None:
        return "undecided"
    return "in" if best.get("in_scope") else "out"


def undecided_folders(root, config):
    """Top-level folders no scope rule touches at all, as (name, .md count).

    The decision list VERIFY works: a folder is here only while nothing anywhere
    inside it has ever been ruled on, so engaging with one subfolder takes the whole
    tree off the list. That is what makes the list drain to empty and stay there,
    and it is why a genuinely new folder stands out at the next sweep without the
    system keeping a separate register of what it has already seen.
    """
    sc = (config or {}).get("scope") or {}
    touched = [str(r.get("path", "")) for r in sc.get("rules", [])]
    out = []
    for name in sorted(os.listdir(root)):
        full = os.path.join(root, name)
        if not os.path.isdir(full) or name.startswith(".") or name == "augment_wiki":
            continue
        if scope_of(name, config) != "undecided":
            continue
        if any(t == name or t.startswith(name + "/") for t in touched):
            continue                      # a rule reaches inside it: already engaged
        n = sum(len(fs) for _, _, fs in os.walk(full)
                for fs in [[f for f in fs if f.endswith(".md")]])
        out.append((name, n))
    return out


def stamp():
    """The current *local* time as `YYYY-MM-DD HH:MM`, the form `updated:` carries (CONTRACT §4).

    A note can be written several times in one day, and a date alone cannot order
    those writes. Local rather than UTC because the person reads these stamps against
    their own day, and because a source written by hand in Obsidian is stamped in local
    time by whatever tooling writes it: one clock for both layers beats a wiki two hours
    out of step with the sources beside it. The offset is not recorded, so a stamp is only meaningful
    in the timezone it was written in; the vault has one author in one place, and the
    checks that read it compare dates, so nothing depends on the finer reading.

    One clock reader lives here so every generator stamps the same way and no script
    re-derives the format; version stamps (CHANGELOG headings, the skill router) stay
    a plain ISO date and use `datetime.date.today()`.
    """
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def split_note(text):
    """Split a wiki note into (frontmatter dict, body text).

    Wiki-note metadata (`type`, `kind`, `keywords`, `status`) lives in YAML
    frontmatter (CONTRACT §4). One parser lives here rather than a regex per
    script, because seven hand-rolled readers is how the three link contexts got
    conflated once already: a single reader means a shape change is made once.
    A note with no frontmatter, or unparseable YAML, yields an empty dict rather
    than raising, so one malformed file cannot abort a whole generator run.
    """
    m = FM.match(text or "")
    if not m:
        return {}, text or ""
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        fm = {}
    return (fm if isinstance(fm, dict) else {}), text[m.end():]


def read_note(path):
    """split_note for a file. Missing file yields ({}, "")."""
    try:
        return split_note(open(path, encoding="utf-8").read())
    except (FileNotFoundError, IsADirectoryError):
        return {}, ""


def links_in(value):
    """The wikilink targets in a frontmatter value, which may be a string or a list.

    `keywords`, `sources`, `type` and `kind` hold quoted wikilinks (`"[[slug]]"`),
    quoted because a bare `[[x]]` is ambiguous YAML. Targets are returned bare,
    so callers compare slugs without re-parsing brackets.

    Deliberately not stripped. A target is literal: six source filenames in this
    vault end in a space (conformance advises renaming them), and trimming here
    would make a link to one resolve against a file that does not exist, reported
    as a dangling link that the note does not actually carry. Whitespace at the
    edge of a slug is a filename problem to be fixed in the filename.
    """
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    out = []
    for it in items:
        out += re.findall(r"\[\[([^\]|]+)", str(it))
    return out


FM_ORDER = ["type", "kind", "status", "generated", "sources", "further_sources", "keywords"]


def fm_block(**fields):
    """Render a wiki-note frontmatter block in canonical key order (CONTRACT §4).

    Order is identity, lifecycle, provenance, navigation: `type`, `kind`, `status`,
    `generated`, `sources`, `further_sources`, `keywords`. `generated` is a nested
    block carrying `by` (the producer that wrote the file, `<producer>/<version>`)
    and `at` (the timestamp that was `updated:` before the OKF alignment).

    Pass `generated_by=` and `generated_at=` as flat keyword arguments; the nesting
    is rendered here so no caller builds YAML by hand. Values are otherwise emitted
    verbatim (already-quoted wikilinks, `#status` strings), keeping generator output
    byte-stable for `write_if_changed`. A key with a None value is omitted, the way
    `kind` is absent on a tension or hub note and `sources` on a theme: an empty
    value is not a value.
    """
    lines = ["---"]
    for k in FM_ORDER:
        if k == "generated":
            by, at = fields.get("generated_by"), fields.get("generated_at")
            if by is None and at is None:
                continue
            lines.append("generated:")
            if by is not None:
                lines.append(f"  by: {by}")
            if at is not None:
                lines.append(f"  at: {at}")
            continue
        v = fields.get(k)
        if v is None:
            continue
        if isinstance(v, list):
            v = "[" + ", ".join(f'"{i}"' for i in v) + "]"
        lines.append(f"{k}: {v}")
    lines.append("---")
    return lines


def write_if_changed(path, text):
    """Write `text` to `path` only if it differs from the existing file once the
    `generated.at` stamp line is normalised out. Returns True if written, False if skipped.

    This keeps the generators idempotent: a run that would change nothing but the
    stamp leaves the file, and its existing stamp, untouched. Without it every hub,
    view and theme body would be rewritten every cycle even when byte-identical,
    which churns the diff and makes the stamp mean "last regenerated" rather than
    "content last changed". With it, it marks the moment the content actually moved.

    The stamp moved from a flat `updated:` line into `generated.at` with the OKF
    alignment, so the normaliser follows it: it matches the indented `at:` line
    inside the `generated` block, anchored to the frontmatter by `count=1` so a
    body line reading `at:` cannot be caught instead.
    """
    def strip_date(t):
        return re.sub(r"(?m)^  at: .*$", "", t, count=1)

    if os.path.exists(path):
        old = open(path, encoding="utf-8").read()
        if strip_date(old) == strip_date(text):
            return False
    open(path, "w", encoding="utf-8").write(text)
    return True
