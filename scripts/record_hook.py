#!/usr/bin/env python3
"""Keep a session's record current without being asked (reference/sessions.md). Hooks only.

Opt-in by the first RECORD: a session whose id has no record (or a closed one) is left
alone, silently and at no cost. For one that has a record:

    record_hook.py --event stop      Stop hook. When the record is older than
                                     `sessions.auto_minutes` (30) and work has moved since
                                     (commits or uncommitted changes in the project, commits
                                     in the vault), or the conversation was compacted since,
                                     it asks Claude for one more turn to re-record. It never
                                     asks twice in a row (`stop_hook_active`).
    record_hook.py --event compact   SessionStart on compaction: marks the record due, so
                                     the next stop re-records whatever its age. A hook cannot
                                     make Claude act before compaction, only after it.
    record_hook.py --event end       SessionEnd: no model, no tokens. Appends the commits and
                                     changed paths since the last record to Touched under a
                                     dated line, stamps `updated`, commits `RECORD: <id> auto`
                                     touching only the record, and pushes.

Silent outside a vault, off the record, or with `sessions: auto: false` in config.yaml.
The session's hook input arrives as JSON on stdin.
"""
import _cli
import datetime, json, os, re, subprocess, sys, tempfile, time
_cli.help_guard()

import _memory as M
import record_write as R
from _gen_util import load_config, stamp


def sh(cwd, *args):
    try:
        r = subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=cwd, capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def off_record(root):
    g = sh(root, "rev-parse", "--absolute-git-dir").strip()
    return bool(g) and os.path.exists(os.path.join(g, "augment-usage", "off"))


def find(root, ids):
    for rid, fm, body in R.load(root):
        if fm.get("status") != "closed" and str(fm.get("session_id", "")) in ids:
            return rid, fm, body
    return None


def last_written(root, rid):
    """When the record was last written, as epoch seconds: its last commit, else the file's mtime."""
    rel = f"{R.DIR}/{rid}.md"
    t = sh(root, "log", "-1", "--format=%ct", "--", rel).strip()
    p = os.path.join(root, rel)
    mt = os.path.getmtime(p) if os.path.exists(p) else 0
    return max(int(t) if t.isdigit() else 0, int(mt))


def moved(repo, since, vault=False):
    """(commit subjects, changed paths) in one repository since an epoch time."""
    if not repo or not sh(repo, "rev-parse", "--git-dir"):
        return [], []
    log = sh(repo, "log", f"--since=@{since}", "--name-only", "--pretty=@@%h %s")
    subjects, paths = [], set()
    for ln in log.splitlines():
        if ln.startswith("@@"):
            subjects.append(ln[2:])
        elif ln.strip():
            paths.add(ln.strip())
    if vault:       # the record's own writes and usage files are not work
        keep = [s for s in subjects if not re.match(r"^\w+ (RECORD|USAGE):", s)]
        paths = {p for p in paths if not p.startswith((f"{R.DIR}/", "augment_wiki/usage"))}
        subjects = keep
    else:
        for ln in sh(repo, "status", "--porcelain").splitlines():
            paths.add(ln[3:].strip())
    return subjects, sorted(paths)


def flag(rid):
    return os.path.join(tempfile.gettempdir(), f"augment-record-{rid}.due")


def main():
    event = sys.argv[sys.argv.index("--event") + 1] if "--event" in sys.argv else ""
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        data = {}
    root = M.resolve_vault()
    if not root:
        return
    cfg = load_config(root)
    s = cfg.get("sessions") or {}
    if s.get("auto") is False or off_record(root):
        return
    ids = {x for x in (os.environ.get("CLAUDE_CODE_REMOTE_SESSION_ID"), data.get("session_id"),
                       os.environ.get("CLAUDE_CODE_SESSION_ID")) if x}
    hit = find(root, ids)
    if not hit:
        return
    rid, fm, body = hit
    project = M.dir_setting(os.environ.get("CLAUDE_PROJECT_DIR")) or data.get("cwd") or os.getcwd()
    project = "" if os.path.abspath(project) == os.path.abspath(root) else project
    since = last_written(root, rid)

    if event == "compact":
        open(flag(rid), "w").close()
        return

    if event == "stop":
        if data.get("stop_hook_active"):
            return
        due = os.path.exists(flag(rid))
        if not due and time.time() - since >= 60 * int(s.get("auto_minutes", 30)):
            due = any(moved(project, since)) or any(moved(root, since, vault=True))
        if not due:
            return
        try:
            os.remove(flag(rid))
        except OSError:
            pass
        when = datetime.datetime.fromtimestamp(since).strftime("%H:%M")
        print(json.dumps({"decision": "block", "reason":
            f"AUGMENT RECORD: this session's record {rid} was last written at {when} and the work has moved since. "
            f"Re-record it now with the record skill: record_write.py write --id {rid}, the five sections rewritten from "
            "where the conversation stands, then commit it as the skill says. State only, nothing else in this turn, "
            "and one line to the person saying the record was updated."}))
        return

    if event == "end":
        commits, paths = moved(project, since)
        vc, vp = moved(root, since, vault=True)
        commits, paths = commits + vc, paths + vp
        if not commits and not paths:
            return
        line = f"- Auto, {stamp()}: " + "; ".join(x for x in (
            ("commits " + ", ".join(commits[:8]) + (" …" if len(commits) > 8 else "")) if commits else "",
            ("changed " + ", ".join(paths[:12]) + (" …" if len(paths) > 12 else "")) if paths else "") if x)
        parts = re.split(r"(?m)^(## Resume\s*$)", body, maxsplit=1)
        if len(parts) != 3:
            return
        new_body = parts[0].rstrip("\n") + "\n" + line + "\n\n" + parts[1] + parts[2]
        fm.update(updated=stamp(), by="augment/record_hook")
        fm["session_url"] = fm.get("session_url") or R.url_of(fm.get("session_id"))
        rel = f"{R.DIR}/{rid}.md"
        open(os.path.join(root, rel), "w", encoding="utf-8", newline="\n").write(R.render(fm, new_body))
        msg = f"RECORD: {rid} auto\n\nAssisted-by: augment/record_hook"
        if sh(root, "add", "--", rel) is not None and sh(root, "commit", "-q", "-m", msg, "--", rel) is not None:
            if subprocess.run(["git", "push", "-q", "origin", "HEAD:main"], cwd=root, capture_output=True, timeout=60).returncode:
                subprocess.run(["git", "pull", "-q", "--no-rebase", "--no-edit", "origin", "main"], cwd=root, capture_output=True, timeout=60)
                subprocess.run(["git", "push", "-q", "origin", "HEAD:main"], cwd=root, capture_output=True, timeout=60)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass        # a hook never breaks the session
