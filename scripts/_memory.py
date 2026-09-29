"""Shared helpers for the memory layer (reference/memory.md). Imported, never invoked.

One reader and one writer of a card's frontmatter, one tokeniser and one
similarity measure, so the writer's duplicate refusal, the search ranking and the
index's merge candidates cannot disagree about what "the same memory" means.
Stdlib plus PyYAML, like the rest of the scripts.
"""
import json, os, re, unicodedata

from _gen_util import load_config, split_note, stamp  # noqa: F401  (re-exported)

DIR = "augment_memory"
CARD_DIR = os.path.join(DIR, "card")
OFFER_DIR = os.path.join(DIR, "offers")
INDEX = os.path.join(DIR, "index.md")
MARKER = os.path.join("augment_wiki", "config.yaml")

TYPES = ("preference", "procedure", "tool", "snippet")   # also the index and context order
STATUSES = ("active", "superseded", "archived")
ORDER = ["type", "title", "summary", "status", "superseded_by", "scope", "keywords",
         "seen", "created", "updated", "by"]
SUMMARY_MAX = 160
TITLE_WORDS = 10
SAME = 0.5          # the writer refuses a new card this close to an active one
CANDIDATE = 0.4     # the index reports active pairs this close as merge candidates

DEFAULTS = {"enabled": True, "index_cap": 150, "inject_chars": 6000, "decay_days": 180}

STOP = set("""a an and are as at be but by can do does for from has have how if in into is it its
not of on or so that the their then there these this to use used uses using was were what when
which while will with without you your via per than also only just more most such""".split())

SECRET = [
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token|token)\b\s*[:=]\s*[\"']?[A-Za-z0-9_\-./+]{12,}"),
]


def settings(root):
    """The `memory:` block of config.yaml over the defaults. Absent means defaults."""
    m = (load_config(root).get("memory") or {})
    return {k: m.get(k, v) for k, v in DEFAULTS.items()}


def dir_setting(v):
    v = (v or "").strip()
    return "" if not v or v.startswith("${") else os.path.abspath(os.path.expanduser(v))


def resolve_vault():
    """The vault as the tier hook finds it: the project directory if it carries the
    marker, else the plugin's vault_path setting. Empty when neither does."""
    for d in (dir_setting(os.environ.get("CLAUDE_PROJECT_DIR")) or os.getcwd(),
              dir_setting(os.environ.get("CLAUDE_PLUGIN_OPTION_VAULT_PATH")),
              dir_setting(os.environ.get("AUGMENT_VAULT"))):
        if d and os.path.isfile(os.path.join(d, MARKER)):
            return d
    return ""


def slugify(title):
    s = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return s[:70].rstrip("-") or "memory"


def fold(text):
    """Lower case with accents dropped, so `réemploi` and `reemploi` are one word."""
    t = unicodedata.normalize("NFKD", str(text))
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def tokens(text):
    out = set()
    for w in re.findall(r"[a-z0-9][a-z0-9_\-]{1,}", fold(text)):
        for part in re.split(r"[_\-]", w) + [w]:
            if len(part) >= 3 and part not in STOP:
                out.add(part[:-1] if part.endswith("s") and len(part) > 4 else part)
    return out


def card_tokens(fm):
    return tokens(" ".join([str(fm.get("title", "")), str(fm.get("summary", "")),
                            " ".join(str(k) for k in as_list(fm.get("keywords")))]))


def jaccard(a, b):
    return len(a & b) / len(a | b) if a and b else 0.0


def as_list(v):
    if v is None or v == "":
        return []
    return [str(x) for x in v] if isinstance(v, list) else [str(v)]


def scopes(fm):
    return [s.lower() for s in as_list(fm.get("scope"))] or ["global"]


def load_cards(root):
    """Every card as (slug, frontmatter, body), sorted by slug."""
    d = os.path.join(root, CARD_DIR)
    out = []
    if not os.path.isdir(d):
        return out
    for f in sorted(os.listdir(d)):
        if f.endswith(".md"):
            text = open(os.path.join(d, f), encoding="utf-8").read()
            fm, body = split_note(text)
            out.append((f[:-3], fm, body))
    return out


def seen_of(fm):
    try:
        return int(fm.get("seen") or 1)
    except (TypeError, ValueError):
        return 1


def sort_cards(cards):
    """Type order first, then the most reinforced, then the most recently touched.
    Stable sorts applied from the least to the most significant key."""
    by_type = {t: i for i, t in enumerate(TYPES)}
    out = sorted(cards, key=lambda c: c[0])
    out.sort(key=lambda c: str(c[1].get("updated", "")), reverse=True)
    out.sort(key=lambda c: seen_of(c[1]), reverse=True)
    out.sort(key=lambda c: by_type.get(c[1].get("type"), 99))
    return out


def secret_in(text):
    for rx in SECRET:
        m = rx.search(text or "")
        if m:
            return m.group(0)[:12] + "..."
    return None


def q(v):
    """A YAML-safe double-quoted scalar. JSON's string form is valid YAML."""
    return json.dumps(str(v), ensure_ascii=False)


def render(fm, body):
    lines = ["---"]
    for k in ORDER:
        v = fm.get(k)
        if v is None or v == "" or v == []:
            continue
        if k in ("title", "summary"):
            lines.append(f"{k}: {q(v)}")
        elif k == "keywords":
            lines.append(f"keywords: [{', '.join(q(x) for x in as_list(v))}]")
        elif k == "scope":
            sc = as_list(v)
            lines.append(f"scope: {sc[0]}" if len(sc) == 1 else f"scope: [{', '.join(q(x) for x in sc)}]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines) + "\n" + body.strip("\n") + "\n"


def n(count, word):
    return f"{count} {word}" + ("" if count == 1 else "s")


def index_line(slug, fm):
    sc = ", ".join(as_list(fm.get("scope")) or ["global"])
    return f"- [{fm.get('type', '?')}] [[{slug}]] ({sc}): {fm.get('summary', '')}"
