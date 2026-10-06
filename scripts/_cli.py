"""Shared command-line guard for the augment scripts. Run, never read (CONTRACT §9).

The scripts take the vault as their first argument, so a leading flag used to be read
as a vault path: `detect_changes.py --help` failed on `--help/augment_wiki/index.jsonl`
and `gen_relations.py --help` regenerated a view as a side effect. These two helpers
make `-h` and `--help` print the script's own docstring and exit before anything is
read or written, and make a script that takes only a vault refuse an unknown leading
flag instead of treating it as a path.
"""
import sys


def help_guard(doc=None):
    """Print the running script's docstring and exit 0 when `-h` or `--help` appears.

    It prints the entry script's own docstring, not the caller's, so a guard that
    fires while one script imports another still shows the script the person ran.
    """
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        main_doc = getattr(sys.modules.get("__main__"), "__doc__", None) or doc
        print((main_doc or "No documentation.").strip())
        sys.exit(0)


def vault_arg(doc=None):
    """The vault path (first argument, else `.`), for a script that takes nothing else.

    Help is answered first. Any other leading flag is an error, never a path.
    """
    help_guard(doc)
    if len(sys.argv) > 1:
        if sys.argv[1].startswith("-"):
            print(f"{sys.argv[0]}: unknown option {sys.argv[1]!r}; the first argument is the "
                  "vault path. Try --help.", file=sys.stderr)
            sys.exit(2)
        return sys.argv[1]
    return "."
