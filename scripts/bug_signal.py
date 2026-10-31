#!/usr/bin/env python3
"""When a plugin script breaks, say so and ask for a proposed fix (skills/dream, Self-improvement).

The scripts rarely change, so a break shows up the day a phase first needs the
script, and the easy move then is to work around it and forget it. This turns the
failure itself into the signal: it reads the output of a run, and when a plugin
script ended in a Python traceback it names the script, the line and the error and
asks for an item in the queue's System observations with a proposed fix. It never
edits the plugin and never blocks; the fix still waits for the person's sign-off.

    bug_signal.py --hook        PostToolUse and PostToolUseFailure on Bash: reads the
                                hook payload on stdin, prints additionalContext or nothing

`runner_mcp.py` appends the same message to a failed run_script result.
"""
import _cli
import json, os, re, sys
_cli.help_guard()

HERE = os.path.dirname(os.path.abspath(__file__))
FRAME = re.compile(r'File "([^"]*?[\\/]scripts[\\/]([A-Za-z0-9_]+)\.py)", line (\d+)')


def message(text):
    """The signal for a run's output, or None when no plugin script raised."""
    if not text or ("Traceback (most recent call last)" not in text and "Error:" not in text):
        return None
    frames = [m for m in FRAME.finditer(text) if os.path.isfile(os.path.join(HERE, m.group(2) + ".py"))]
    if not frames:
        return None
    last = frames[-1]
    tail = text[last.end():]
    err = next((l.strip() for l in reversed(tail.splitlines()) if re.match(r"\s*[A-Za-z_.]*(Error|Exception)\b", l)), None)
    if not err:
        return None
    return (f"AUGMENT BUG: plugin script {last.group(2)}.py failed at line {last.group(3)}: {err}. "
            "Do not route around it silently. Add an item to the System observations in "
            "augment_wiki/verify-queue.md: what broke, where (script and line), and a proposed fix, "
            "with the diff when it is small. The fix itself waits for the person's sign-off; "
            "continue with a workaround if one exists and say so in your reply.")


def _flatten(v):
    if isinstance(v, dict):
        return "\n".join(_flatten(x) for x in v.values())
    if isinstance(v, list):
        return "\n".join(_flatten(x) for x in v)
    return v if isinstance(v, str) else ""


def main():
    if "--hook" not in sys.argv:
        print(__doc__.strip())
        return
    try:
        d = json.load(sys.stdin)
    except Exception:
        return
    text = _flatten(d.get("tool_response")) + "\n" + _flatten(d.get("error"))
    msg = message(text)
    if msg:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": d.get("hook_event_name", "PostToolUse"),
                                                 "additionalContext": msg}}))


if __name__ == "__main__":
    main()
