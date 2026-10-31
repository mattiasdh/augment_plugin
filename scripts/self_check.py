#!/usr/bin/env python3
"""The plugin checks itself: does every script still run here (skills/dream, Self-improvement).

A script that no longer parses on the interpreter the nightly cycle runs fails only
when its phase is reached, and then gets worked around in the moment rather than
fixed. This runs first in the cycle so the break is found before any phase needs the
script, and its findings go to the system-observations list like any other friction.
It detects; it never edits the plugin.

Two checks, both deterministic:

  1. Every `scripts/*.py` compiles under the running `python3`. The cloud container
     runs 3.11, so syntax newer than that (a backslash inside an f-string
     expression, PEP 701) is caught where it would break.
  2. Every `scripts/<name>.py` a hook, skill, rule or reference names exists, so a
     renamed script cannot leave a dangling call behind.

    self_check.py [<plugin root>]      default: the plugin this script belongs to

Prints `OK` and the interpreter version, or one line per finding; exit 1 on any finding.
"""
import _cli
import glob, os, re, sys
_cli.help_guard()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    root = os.path.abspath(args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    found = []
    for p in sorted(glob.glob(os.path.join(root, "scripts", "*.py"))):
        try:
            compile(open(p, encoding="utf-8").read(), p, "exec")
        except SyntaxError as e:
            found.append(f"DOES NOT PARSE scripts/{os.path.basename(p)}:{e.lineno}: {e.msg}")
    named = set()
    for d in ("hooks", "skills", "rules", "reference"):
        for p in glob.glob(os.path.join(root, d, "**", "*"), recursive=True):
            if os.path.isfile(p) and p.endswith((".md", ".json")):
                txt = open(p, encoding="utf-8").read()
                for m in re.finditer(r"scripts/([a-z_][a-z0-9_]+)\.py", txt):
                    named.add((m.group(1), os.path.relpath(p, root)))
    for name, where in sorted(named):
        if not os.path.isfile(os.path.join(root, "scripts", name + ".py")):
            found.append(f"MISSING SCRIPT scripts/{name}.py, named in {where}")
    v = ".".join(map(str, sys.version_info[:3]))
    for f in found:
        print(f)
    if found:
        print(f"{len(found)} finding(s) on Python {v}")
        sys.exit(1)
    print(f"OK: {len(glob.glob(os.path.join(root, 'scripts', '*.py')))} scripts parse on Python {v}; every named script exists")


if __name__ == "__main__":
    main()
