#!/usr/bin/env python3
"""Record which wiki notes and memory cards are used (reference/scope-and-index.md, Usage).

Nothing is written into a note, a card or the index. A reading session only drops
one small file into `augment_wiki/usage.pending/`; the nightly cycle's
`compact_index.py` folds it into the append-only `augment_wiki/usage.jsonl` and
projects the counts onto the index, so the index keeps a single writer.

Three kinds of event, kept apart:

  open   a wiki note or memory card was read. Recorded automatically by a
         PostToolUse hook on Read in Code and Cowork, and by the connector's
         vault_read and memory_get.
  cite   a wiki note was cited in an answer or a discussion (answer, discuss).
  apply  a memory card was applied (recall).

Events gather in a buffer inside `.git/` (never untracked noise) and reach `main`
as one `USAGE:` commit holding only the pending file: the Stop hook flushes at
most every fifteen minutes, SessionEnd always. This is the one named exception to
"read-only work never commits". A git failure leaves the buffer for the next
flush and says nothing. Stdlib only, since it runs on every Read.

    usage_log.py --hook                      PostToolUse on Read: stdin is the hook JSON
    usage_log.py --flush --hook [--end]      Stop (or SessionEnd with --end)
    usage_log.py <vault> --kind cite|apply --op answer|discuss|recall <path-or-slug>...
    usage_log.py <vault> --off               off the record: nothing is recorded or
                                             flushed until the session ends
    usage_log.py <vault> --flush [--end]     flush by hand (in Tier 2, before commit-and-sync)

Silent outside a vault, and when `usage: enabled: false` in config.yaml.
"""
import _cli
import datetime, glob, json, os, re, subprocess, sys, time
_cli.help_guard()

MARKER = os.path.join("augment_wiki", "config.yaml")
PENDING = os.path.join("augment_wiki", "usage.pending")
WIKI_DIRS = ("concept", "entity", "theme", "tension", "hub")
FLUSH_EVERY = 15 * 60
ANY = "any"   # the buffer used by explicit calls outside a hook, when no session id is known


def dir_setting(v):
    v = (v or "").strip()
    return "" if not v or v.startswith("${") else os.path.abspath(os.path.expanduser(v))


def resolve_vault(cwd=""):
    """The vault as the tier hook finds it (`_memory.resolve_vault`, without PyYAML)."""
    for d in (dir_setting(os.environ.get("CLAUDE_PROJECT_DIR")) or dir_setting(cwd) or os.getcwd(),
              dir_setting(os.environ.get("CLAUDE_PLUGIN_OPTION_VAULT_PATH")),
              dir_setting(os.environ.get("AUGMENT_VAULT"))):
        if d and os.path.isfile(os.path.join(d, MARKER)):
            return d
    return ""


def enabled(root):
    """`usage: enabled:` from config.yaml, read without a YAML parser: default true."""
    try:
        text = open(os.path.join(root, MARKER), encoding="utf-8").read()
    except OSError:
        return False
    m = re.search(r"^usage:\s*\n((?:[ \t]+.*\n?|\s*\n)*)", text, re.M)
    if not m:
        return True
    e = re.search(r"^[ \t]+enabled:\s*(\w+)", m.group(1), re.M)
    return not (e and e.group(1).lower() in ("false", "no", "off", "0"))


def tracked(root, path):
    """The vault-relative id when `path` is a wiki note or a memory card, else ""."""
    p = os.path.abspath(os.path.join(root, path)) if not os.path.isabs(path) else os.path.abspath(path)
    try:
        rel = os.path.relpath(p, root).replace(os.sep, "/")
    except ValueError:
        return ""
    if rel.startswith("../") or not rel.endswith(".md"):
        return ""
    parts = rel.split("/")
    if len(parts) == 3 and parts[0] == "augment_wiki" and parts[1] in WIKI_DIRS:
        return rel
    if len(parts) == 3 and parts[0] == "augment_memory" and parts[1] == "card":
        return rel
    return ""


def resolve_id(root, ref):
    """A path, or a bare slug looked up among the wiki notes and the cards."""
    rel = tracked(root, ref)
    if rel:
        return rel
    slug = os.path.basename(ref).removesuffix(".md")
    hits = [h for h in glob.glob(os.path.join(root, "augment_wiki", "*", slug + ".md"))
            + glob.glob(os.path.join(root, "augment_memory", "card", slug + ".md"))]
    hits = [tracked(root, h) for h in hits]
    hits = [h for h in hits if h]
    return hits[0] if len(hits) == 1 else ""


def git_dir(root):
    d = os.path.join(root, ".git")
    if os.path.isdir(d):
        return d
    try:
        out = subprocess.run(["git", "rev-parse", "--absolute-git-dir"], cwd=root,
                             capture_output=True, text=True, timeout=10).stdout.strip()
        return out
    except Exception:
        return ""


def buf_dir(root):
    g = git_dir(root)
    if not g:
        return ""
    d = os.path.join(g, "augment-usage")
    os.makedirs(d, exist_ok=True)
    return d


def is_off(bd):
    return os.path.exists(os.path.join(bd, "off"))


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def session_key(s):
    s = re.sub(r"[^A-Za-z0-9]", "", str(s or ""))[:8]
    return s or ANY


def record(root, session, kind, ids, op, surface="code"):
    """Append events to the session's buffer; an open is kept once per id per session."""
    if not ids or not enabled(root):
        return 0
    bd = buf_dir(root)
    if not bd or is_off(bd):
        return 0
    path = os.path.join(bd, session_key(session) + ".jsonl")
    have = set()
    if kind == "open" and os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("kind") == "open":
                have.add(d.get("id"))
    stamp, n = now(), 0
    with open(path, "a", encoding="utf-8") as f:
        for i in ids:
            if kind == "open" and i in have:
                continue
            have.add(i)
            f.write(json.dumps({"at": stamp, "kind": kind, "id": i, "op": op, "surface": surface,
                                "session": session_key(session)}, ensure_ascii=False) + "\n")
            n += 1
    return n


def git(root, *args, timeout=60):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=timeout)


def flush(root, session=None, end=False, push=True):
    """Move unflushed buffer lines into one pending file, commit only that file, push to main.

    Returns a one-line report, or "" when there was nothing to do."""
    bd = buf_dir(root)
    if not bd:
        return ""
    if is_off(bd):
        # Off the record: what was gathered while off is dropped, never committed.
        for f in glob.glob(os.path.join(bd, "*.jsonl")):
            os.remove(f)
        if end:
            os.remove(os.path.join(bd, "off"))
        return ""
    if not enabled(root):
        return ""
    stamp_file = os.path.join(bd, "last-flush")
    if not end and os.path.exists(stamp_file) and time.time() - os.path.getmtime(stamp_file) < FLUSH_EVERY:
        return ""
    lines = []
    files = sorted(glob.glob(os.path.join(bd, "*.jsonl")))
    for f in files:
        lines += [l for l in open(f, encoding="utf-8") if l.strip()]
    if not lines:
        return ""
    sess = session_key(session) if session else session_key(json.loads(lines[0]).get("session"))
    os.makedirs(os.path.join(root, PENDING), exist_ok=True)
    # Never an existing name: two flushes in one second must not overwrite each other.
    name = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{sess}-{os.urandom(3).hex()}.jsonl"
    rel = f"{PENDING}/{name}".replace(os.sep, "/")
    with open(os.path.join(root, rel), "x", encoding="utf-8", newline="\n") as out:
        out.writelines(l if l.endswith("\n") else l + "\n" for l in lines)
    for f in files:
        os.remove(f)
    open(stamp_file, "w").close()
    kinds = [json.loads(l).get("kind") for l in lines]
    msg = (f"USAGE: {kinds.count('open')} opens, {kinds.count('cite')} citations, "
           f"{kinds.count('apply')} cards applied")
    try:
        if git(root, "add", "--", rel).returncode:
            return f"usage written to {rel}, not committed"
        if git(root, "commit", "-q", "-m", msg, "--", rel).returncode:
            return f"usage written to {rel}, not committed"
        if not push:
            return f"{msg} (committed, not pushed)"
        if git(root, "push", "-q", "origin", "HEAD:main").returncode:
            # Behind main: merge (the file name is unique, so it cannot conflict) and retry once.
            if git(root, "pull", "-q", "--no-rebase", "--no-edit", "origin", "main").returncode == 0:
                git(root, "push", "-q", "origin", "HEAD:main")
    except Exception:
        return f"usage written to {rel}, not pushed"
    return msg


def hook():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    root = resolve_vault(data.get("cwd", ""))
    if not root:
        return
    session = data.get("session_id")
    if "--flush" in sys.argv:
        flush(root, session, end="--end" in sys.argv or data.get("hook_event_name") == "SessionEnd")
        return
    if data.get("tool_name") != "Read":
        return
    path = str((data.get("tool_input") or {}).get("file_path") or "")
    rel = tracked(root, path) if path else ""
    if rel:
        record(root, session, "open", [rel], "read")


def main():
    if "--hook" in sys.argv:
        try:
            hook()
        except Exception:
            pass            # a usage hook never interrupts the work
        return
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = sys.argv[1:]
    root = os.path.abspath(args[0]) if args else resolve_vault()
    if not root or not os.path.isfile(os.path.join(root, MARKER)):
        sys.exit("no augment vault here; give the vault path first")
    if "--off" in flags:
        bd = buf_dir(root)
        if bd:
            open(os.path.join(bd, "off"), "w").close()
        print("usage: off the record until this session ends; nothing gathered from now on is committed")
        return
    if "--flush" in flags:
        print(flush(root, end="--end" in flags) or "usage: nothing to flush")
        return
    def opt(name, default=None):
        return flags[flags.index(name) + 1] if name in flags and flags.index(name) + 1 < len(flags) else default
    kind, op = opt("--kind"), opt("--op", "")
    if kind not in ("cite", "apply", "open"):
        sys.exit("--kind must be cite, apply or open")
    values = {opt("--kind"), opt("--op"), opt("--surface")}
    refs = [a for a in args[1:] if a not in values]
    ids, unknown = [], []
    for r in refs:
        i = resolve_id(root, r)
        (ids if i else unknown).append(i or r)
    n = record(root, os.environ.get("CLAUDE_SESSION_ID"), kind, ids, op or kind,
               surface=opt("--surface", "code"))
    print(f"usage: {n} {kind} event(s) recorded" + (f"; not a wiki note or card: {', '.join(unknown)}" if unknown else ""))


if __name__ == "__main__":
    main()
