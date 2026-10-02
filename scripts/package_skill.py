#!/usr/bin/env python3
"""Package a vault-held skill for upload, and check the skills root (reference/skills.md).

A skill kept in the vault lives in one folder under the skills root that
`config.yaml` declares: its thin SKILL.md, the reference files it reads live on
every use, a CHANGELOG.md of approved rule changes, and `dist/<skill>.skill`, the
upload package this script builds. The package is the fallback a session uses
when no vault is connected, so it is never edited by hand: change the references,
then rebuild.

The build is deterministic: entries sorted, timestamps fixed, and a stamp line
added to the packaged SKILL.md naming the last CHANGELOG date and a hash of the
content, so a rebuild of unchanged files is byte-identical and writes nothing.
Left out of the package: `dist/`, CHANGELOG.md, README.md, dotfiles and any
`_`-prefixed folder (`_archive/`, for superseded versions kept for the record).
A folder under the root that carries `.claude-plugin/` is a plugin's review copy,
not a skill, and the checks pass over it.

    package_skill.py <vault> <skill>        build dist/<skill>.skill when it changed
    package_skill.py <vault> --all          every skill folder with a SKILL.md
    package_skill.py <vault> --check        report skill-folder problems, write nothing
"""
import argparse, hashlib, io, os, re, sys, zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _gen_util import skills_root, split_note

LEFT_OUT = {"CHANGELOG.md", "README.md"}
EPOCH = (1980, 1, 1, 0, 0, 0)


def skill_dirs(root):
    """Every folder directly under the skills root, as (name, absolute path)."""
    sr = skills_root(root)
    base = os.path.join(root, sr) if sr else ""
    if not sr or not os.path.isdir(base):
        return []
    return [(d, os.path.join(base, d)) for d in sorted(os.listdir(base))
            if os.path.isdir(os.path.join(base, d)) and not d.startswith((".", "_"))]


def packaged_files(d):
    out = []
    for dirpath, dirnames, filenames in os.walk(d):
        rel = os.path.relpath(dirpath, d)
        dirnames[:] = sorted(x for x in dirnames if not x.startswith((".", "_")) and not (rel == "." and x == "dist"))
        for f in sorted(filenames):
            if f.startswith(".") or (rel == "." and f in LEFT_OUT):
                continue
            out.append(os.path.normpath(os.path.join(rel, f)).replace(os.sep, "/"))
    return sorted(out)


def last_change(d):
    p = os.path.join(d, "CHANGELOG.md")
    dates = re.findall(r"\b(20\d\d-\d\d-\d\d)\b", open(p, encoding="utf-8").read()) if os.path.isfile(p) else []
    return max(dates) if dates else "undated"


def stamp_skill(text, line):
    """Insert the snapshot line after the frontmatter, so the uploaded skill states what it is."""
    m = re.match(r"(---\n.*?\n---\n)", text, re.S)
    head, rest = (m.group(1), text[m.end():]) if m else ("", text)
    return f"{head}\n> {line}\n{rest}"


def build(name, d):
    """The package bytes for one skill folder. Pure: same files, same bytes."""
    files = packaged_files(d)
    h = hashlib.sha256()
    for f in files:
        h.update(f.encode() + b"\0" + open(os.path.join(d, f), "rb").read() + b"\0")
    line = (f"Packaged snapshot of the vault's references (last approved change {last_change(d)}, "
            f"content {h.hexdigest()[:8]}). With the vault connected, read the live files instead, "
            f"as the Files section says.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            data = open(os.path.join(d, f), "rb").read()
            if f == "SKILL.md":
                data = stamp_skill(data.decode("utf-8"), line).encode("utf-8")
            info = zipfile.ZipInfo(f"{name}/{f}", date_time=EPOCH)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)
    return buf.getvalue()


def dist_path(name, d):
    return os.path.join(d, "dist", f"{name}.skill")


def check(root):
    """(defects, advisories) for the skills root. Skills are out of the wiki, so
    nothing here fails a build; conformance reports both as advisories."""
    issues = []
    sr = skills_root(root)
    for name, d in skill_dirs(root):
        rel = f"{sr}/{name}"
        if os.path.isdir(os.path.join(d, ".claude-plugin")):
            continue
        sk = os.path.join(d, "SKILL.md")
        if not os.path.isfile(sk):
            issues.append(f"skills: {rel} has no SKILL.md at its top, so it is not a skill folder (an archive, "
                          "a nested copy or a plugin): flatten it, or move it out of the skills root")
            continue
        text = open(sk, encoding="utf-8").read()
        fm, body = split_note(text)
        raw = re.match(r"---\n(.*?)\n---", text, re.S)
        if not fm and raw and re.search(r"(?m)^name:", raw.group(1)):
            issues.append(f"skills: {rel}/SKILL.md frontmatter is not valid YAML (often an unquoted ': ' inside "
                          "the description); quote the description so every loader reads it the same way")
        elif not fm.get("name") or not fm.get("description"):
            issues.append(f"skills: {rel}/SKILL.md lacks a name or description in its frontmatter")
        elif str(fm.get("name")) != name:
            issues.append(f"skills: {rel}/SKILL.md is named {fm.get('name')!r}, its folder {name!r}")
        for ref in sorted(set(re.findall(r"(?<![\w/:])references/[\w.+\-]+(?: [\w.+\-]+)*?\.md\b", body))):
            if not os.path.isfile(os.path.join(d, ref)):
                issues.append(f"skills: {rel}/SKILL.md names {ref}, which does not exist")
        dp = dist_path(name, d)
        if os.path.isfile(dp) and open(dp, "rb").read() != build(name, d):
            issues.append(f"skills: {rel}/dist/{name}.skill is behind its live files; "
                          f"run package_skill.py . {name} and upload the package again")
    return issues


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("vault")
    ap.add_argument("skill", nargs="?")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.vault)
    if not skills_root(root):
        sys.exit("no skills root: declare `skills: root: <folder>` in augment_wiki/config.yaml")
    if a.check:
        issues = check(root)
        for i in issues:
            print(i)
        print(f"skills: {len(skill_dirs(root))} folders, {len(issues)} issue(s)")
        return
    dirs = dict(skill_dirs(root))
    names = [n for n in dirs if os.path.isfile(os.path.join(dirs[n], "SKILL.md"))] if a.all else [a.skill]
    if not names or names == [None]:
        sys.exit("name a skill, or pass --all")
    for name in names:
        if name not in dirs or not os.path.isfile(os.path.join(dirs[name], "SKILL.md")):
            sys.exit(f"no skill folder {name} with a SKILL.md under {skills_root(root)}")
        data, dp = build(name, dirs[name]), dist_path(name, dirs[name])
        if os.path.isfile(dp) and open(dp, "rb").read() == data:
            print(f"{name}: dist/{name}.skill unchanged")
            continue
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        open(dp, "wb").write(data)
        print(f"{name}: dist/{name}.skill written ({len(packaged_files(dirs[name]))} files, {len(data)} bytes); "
              "upload it to claude.ai to replace the previous version")


if __name__ == "__main__":
    main()
