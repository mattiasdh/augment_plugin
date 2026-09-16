#!/usr/bin/env python3
"""Re-assert WRITE_FLOW's mechanical register on a prose-shaped prompt.

WRITE_FLOW §0 binds every piece of prose the model writes, chat replies
included where prose is the deliverable, not only what lands in the vault.
Nothing about that scope survives context compaction on its own: the register
was live at the start of a session and still drifted mid-session once nothing
re-asserted it. `/taste anchor` names the same limit in its own SKILL.md
("persistence is best-effort... until context is compacted") rather than
solving it.

The one thing that survives compaction is a hook that fires fresh every turn.
`check_freshness.py` already does this for freshness; this does it for the
register, but only on turns that look prose-shaped, so it costs nothing on
the many turns where no prose deliverable is being asked for.

Reads the UserPromptSubmit envelope on stdin (`{"prompt": "..."}`) and, only
if the prompt matches a drafting-shaped trigger, emits the mechanical rules
from WRITE_FLOW §2 as additionalContext. Silent otherwise: emits nothing and
exits 0, so a non-matching turn costs nothing beyond the regex.

    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/write_flow_register.py" --hook

The trigger list is deliberately narrow and mechanical, not a judgment call:
false negatives (an unusual phrasing that slips past) are the accepted
failure mode, in exchange for firing on no turn that plainly doesn't need it.
"""
import os, json, re, sys

HOOK = "--hook" in sys.argv

TRIGGER = re.compile(
    r"\b("
    r"write|draft|rewrite|redraft|compose|"
    r"r[ée]dige[rz]?|r[ée][ée]cri[rt]|"
    r"schrijf|herschrijf|opstel(len)?|"
    r"chapter|section|chapitre|hoofdstuk|paragraph|paragraphe|"
    r"callout|footnote|"
    r"email|e-mail|mail|letter|memo|report|rapport|"
    r"summary|synthèse|samenvatting"
    r")\b",
    re.IGNORECASE,
)

REGISTER = (
    "WRITE_FLOW register (applies only where THIS reply's own prose is a "
    "deliverable, a drafted chapter, email, summary, callout, not routine "
    "conversational replies): flowing paragraphs, never hard-wrapped. No em "
    "dashes, no middle dots; en dashes only for ranges or a paired aside. One "
    "bolded claim per section, never for emphasis. Cut on sight: colon reveals, "
    "faux-insight openers (\"what most people miss\"), importance puffery, "
    "profound closing lines, summary-recap endings, synonym cycling, "
    "superficial -ing analysis. Never claim the artefact's own quality "
    "(\"this analysis shows...\", \"as demonstrated above...\")."
)


def in_vault(root):
    """True where `root` is an augment vault, by its marker file.

    A plugin-shipped hook fires in every project where the plugin is enabled, so
    each entry point checks for the marker and exits silently when it is absent.
    Without this the freshness hook would fetch in unrelated repositories and the
    register hook would fire in projects that have no wiki. Both layouts are
    accepted while a vault migrates from the older one.
    """
    return any(os.path.exists(os.path.join(root, p)) for p in
               ("augment_wiki/config.yaml", "_augment/config.yaml"))


def main():
    if not in_vault(os.environ.get("CLAUDE_PROJECT_DIR", ".")):
        return 0
    try:
        payload = json.load(sys.stdin)
        prompt = payload.get("prompt", "")
    except (json.JSONDecodeError, AttributeError):
        prompt = ""

    if not TRIGGER.search(prompt):
        return 0

    if HOOK:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit", "additionalContext": REGISTER}}))
    else:
        print(REGISTER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
