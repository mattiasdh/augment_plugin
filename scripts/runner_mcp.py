#!/usr/bin/env python3
"""augment-runner: the pinned scripts, served over MCP to a surface with no shell.

Tier 2 (rules/surfaces.md) reaches the vault through Obsidian's Local REST API
MCP, which reads, writes, searches and runs Obsidian commands but cannot execute
anything. Every operation that leans on a script (freshness, change detection,
compaction, backlinks, the generated views, conformance, byte-preserving source
writes) would otherwise have to be reimplemented by the model, which the method
forbids. This server closes that gap and nothing more: it runs on the person's
machine, beside the vault, as a stdio MCP server bundled in the plugin.

Tools:

  status          the vault it resolved, whether the marker is there, Python and
                  PyYAML, the plugin version. The tier gate's probe.
  run_script      one script from this directory, by name, with an argument list,
                  cwd fixed to the vault, no shell. Pass the vault as ".".
  append_history  JSON objects appended to augment_wiki/history.jsonl, one per
                  line, validated first and written byte-exactly.
  scratch_write   a working file outside the vault (a draft for rewrite_check,
                  say), passed to a script afterwards as `scratch/<name>`.

It writes to the vault only through those scripts and the history append. It
never runs git beyond what a script does itself (check_freshness fetches);
pulling, committing and pushing stay with Obsidian Git so the repository has one
writer. Stdlib only, newline-delimited JSON-RPC 2.0 on stdin/stdout.

The vault is AUGMENT_VAULT (the plugin's `vault_path` setting), else
AUGMENT_PROJECT_DIR or the working directory when either carries
`augment_wiki/config.yaml`. With none, it still starts and reports unavailable,
so the gate can tell the person what to connect instead of the client showing a
dead server.
"""
import json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MARKER = os.path.join("augment_wiki", "config.yaml")
EXCLUDED = {"runner_mcp", "migrate_hash_v2", "write_flow_register"}
TIMEOUT = 600
MAX_OUT = 100_000
PROTOCOL = "2025-06-18"
SCRATCH = os.path.join(tempfile.gettempdir(), "augment-scratch")


def _setting(name):
    v = os.environ.get(name, "").strip()
    return "" if not v or v.startswith("${") else os.path.abspath(os.path.expanduser(v))


def resolve_vault():
    configured = _setting("AUGMENT_VAULT")
    if configured:
        return configured, "vault_path setting"
    for d, where in ((_setting("AUGMENT_PROJECT_DIR"), "project directory"), (os.getcwd(), "working directory")):
        if d and os.path.isfile(os.path.join(d, MARKER)):
            return d, where
    return "", ""


def scripts():
    return sorted(f[:-3] for f in os.listdir(HERE)
                  if f.endswith(".py") and not f.startswith("_") and f[:-3] not in EXCLUDED)


def plugin_version():
    try:
        return json.load(open(os.path.join(ROOT, ".claude-plugin", "plugin.json")))["version"]
    except Exception:
        return "unknown"


def tool_status(_):
    vault, how = resolve_vault()
    has_marker = bool(vault) and os.path.isfile(os.path.join(vault, MARKER))
    try:
        import yaml  # noqa: F401
        has_yaml = True
    except ImportError:
        has_yaml = False
    lines = [f"plugin_version: {plugin_version()}",
             f"python: {sys.version.split()[0]} ({sys.executable})",
             f"pyyaml: {'yes' if has_yaml else 'MISSING (pip3 install pyyaml)'}"]
    if not vault:
        lines.insert(0, "UNAVAILABLE: no vault. Set the plugin's vault_path to the folder holding augment_wiki/config.yaml.")
    elif not has_marker:
        lines.insert(0, f"UNAVAILABLE: {vault} ({how}) has no augment_wiki/config.yaml.")
    elif not has_yaml:
        lines.insert(0, f"UNAVAILABLE: vault at {vault} ({how}), but PyYAML is missing, so the scripts cannot read config.yaml.")
    else:
        lines.insert(0, f"READY: vault at {vault} ({how}).")
    return "\n".join(lines), not lines[0].startswith("READY")


def _clip(s):
    if len(s) <= MAX_OUT:
        return s
    keep = MAX_OUT // 5
    return s[:keep] + f"\n[... {len(s) - MAX_OUT} characters cut ...]\n" + s[-(MAX_OUT - keep):]


def tool_run_script(args):
    vault, _ = resolve_vault()
    if not vault or not os.path.isfile(os.path.join(vault, MARKER)):
        return tool_status({})[0], True
    name = str(args.get("script", "")).removesuffix(".py")
    if name not in scripts():
        return f"REFUSED: '{name}' is not one of: {', '.join(scripts())}", True
    argv = args.get("args") or ["."]
    if not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
        return "REFUSED: args must be a list of strings", True
    argv = ["." if a == "<vault>" else
            os.path.join(SCRATCH, os.path.basename(a[8:])) if a.startswith("scratch/") else a
            for a in argv]
    try:
        p = subprocess.run([sys.executable, os.path.join(HERE, name + ".py"), *argv],
                           cwd=vault, capture_output=True, text=True, timeout=TIMEOUT,
                           env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    except subprocess.TimeoutExpired:
        return f"TIMEOUT after {TIMEOUT}s: {name}", True
    out = (p.stdout or "") + (("\n[stderr]\n" + p.stderr) if p.stderr.strip() else "")
    return _clip(f"$ {name}.py {' '.join(argv)}\n[exit {p.returncode}]\n{out}"), p.returncode != 0


def tool_append_history(args):
    vault, _ = resolve_vault()
    if not vault or not os.path.isfile(os.path.join(vault, MARKER)):
        return tool_status({})[0], True
    entries = args.get("entries")
    if not isinstance(entries, list) or not entries:
        return "REFUSED: entries must be a non-empty list of objects", True
    for i, e in enumerate(entries):
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not e["id"]:
            return f"REFUSED: entry {i} is not an object with a string id; nothing written", True
    path = os.path.join(vault, "augment_wiki", "history.jsonl")
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        if size:
            f.seek(size - 1)
            last = f.read(1)
    data = "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries).encode("utf-8")
    with open(path, "ab") as f:
        if size and last != b"\n":
            f.write(b"\n")
        f.write(data)
    return f"appended {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} to augment_wiki/history.jsonl; run compact_index next", False


def tool_scratch_write(args):
    name = os.path.basename(str(args.get("name", "")))
    if not name or name.startswith("."):
        return "REFUSED: name must be a plain file name", True
    content = args.get("content")
    if not isinstance(content, str):
        return "REFUSED: content must be a string", True
    os.makedirs(SCRATCH, exist_ok=True)
    with open(os.path.join(SCRATCH, name), "w", encoding="utf-8", newline="") as f:
        f.write(content)
    return f"wrote scratch/{name} ({len(content)} characters); pass it to a script as scratch/{name}", False


TOOLS = [
    {"name": "status",
     "description": "Report whether the augment vault is reachable on this machine: the resolved vault path, the marker file, Python and PyYAML. Call first in a Tier 2 session (rules/surfaces.md); anything but READY means stop and ask the person to connect.",
     "inputSchema": {"type": "object", "properties": {}},
     "fn": tool_status},
    {"name": "run_script",
     "description": "Run one of the augment plugin's pinned scripts against the vault (cwd is the vault, so pass the vault as \".\"). The Tier 2 equivalent of `python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/<script>.py\" <args>` in the skills. Returns the exit code and output.",
     "inputSchema": {"type": "object",
                     "properties": {"script": {"type": "string", "description": "Script name without .py, e.g. check_freshness, detect_changes, compact_index, sync_backlinks, conformance, gen_hubs, source_write."},
                                    "args": {"type": "array", "items": {"type": "string"}, "description": "Arguments, vault first as \".\", e.g. [\".\"] or [\".\", \"set\", \"notes/x.md\", \"augment\", \"#processed #linked\"]."}},
                     "required": ["script"]},
     "fn": tool_run_script},
    {"name": "append_history",
     "description": "Append entries to augment_wiki/history.jsonl, the append-only ledger, one JSON object per line. Each entry needs a string id. Always follow with run_script compact_index.",
     "inputSchema": {"type": "object",
                     "properties": {"entries": {"type": "array", "items": {"type": "object"}}},
                     "required": ["entries"]},
     "fn": tool_append_history},
    {"name": "scratch_write",
     "description": "Write a working file outside the vault, e.g. a draft to compare with rewrite_check. Refer to it in run_script args as scratch/<name>. The Tier 2 stand-in for a scratchpad file.",
     "inputSchema": {"type": "object",
                     "properties": {"name": {"type": "string"}, "content": {"type": "string"}},
                     "required": ["name", "content"]},
     "fn": tool_scratch_write},
]
BY_NAME = {t["name"]: t for t in TOOLS}


def handle(msg):
    method, mid = msg.get("method"), msg.get("id")
    if mid is None:
        return None  # a notification
    if method == "initialize":
        asked = (msg.get("params") or {}).get("protocolVersion") or PROTOCOL
        result = {"protocolVersion": asked,
                  "capabilities": {"tools": {}},
                  "serverInfo": {"name": "augment-runner", "version": plugin_version()},
                  "instructions": "Runs the augment plugin's scripts beside the vault. Tier gate: call status first; see the plugin's rules/surfaces.md."}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{k: v for k, v in t.items() if k != "fn"} for t in TOOLS]}
    elif method == "tools/call":
        params = msg.get("params") or {}
        tool = BY_NAME.get(params.get("name"))
        if not tool:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"unknown tool {params.get('name')}"}}
        try:
            text, is_error = tool["fn"](params.get("arguments") or {})
        except Exception as e:  # report, never crash the server
            text, is_error = f"ERROR: {type(e).__name__}: {e}", True
        result = {"content": [{"type": "text", "text": text}], "isError": is_error}
    else:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            out = handle(msg) if isinstance(msg, dict) else None
        if out is not None:
            sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
