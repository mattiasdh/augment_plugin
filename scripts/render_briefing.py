#!/usr/bin/env python3
"""The morning briefing as one HTML page, and the index of every briefing (skills/brief).

The newest dated briefing, `augment_wiki/view/briefings/briefing-YYYYMMDD.md` (or the one
`--file` names), is laid out as the page; `augment_wiki/view/briefing.md` is rewritten as
the index: the latest briefing, then every earlier one, newest first. Nothing is deleted.

Deterministic: the note is the briefing, written by the model from gen_briefing.py's
facts; this only lays it out, so the page and the note never disagree and no model call
is spent on markup. The layout follows the morning skill's: a calm top band (the date,
one headline, the most active projects as three short columns) and a bottom band of
plain numbered lists, one per section of the note.

    render_briefing.py <vault> [--file PATH] [--out PATH]      --out default: the runner's scratch, <tmp>/augment-scratch/briefing.html

Links: a wikilink `[[path|label]]` becomes an `obsidian://open` link into the vault
(`briefing.obsidian_vault`, default the vault folder's name), so a tap on the phone opens
the note in Obsidian; the label is always shown as text, since a custom-scheme link may
do nothing inside an artifact. The page title is `briefing.title` (default "Morning
Briefing"). Prints the path written.
"""
import _cli
import argparse, datetime, html, os, re, sys, tempfile, urllib.parse
_cli.help_guard()

from _gen_util import fm_block, load_config, split_note, stamp, write_if_changed
from gen_briefing import DATED, VIEW, dated

EARLIER = 7          # earlier briefings linked from the page's footer

CSS = """
/* Layout: two full-bleed bands meeting at a hairline; a calm top band (date, headline, project columns), lists below. */
:root {
  --bg: #FCFCFB; --wash: #F9F9F7; --ink: #2E2C27; --ink-soft: #6B6A63; --ink-grey: #A9A89D;
  --hairline: #E4E3DC; --edge: #E1E1DF; --clay: #C6613F;
  --serif: "Fraunces", Georgia, "Times New Roman", serif;
  --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #1C1B19; --wash: #22211E; --ink: #EDEBE4; --ink-soft: #ADABA1; --ink-grey: #6F6D65;
  --hairline: #34322E; --edge: #3A3833; --clay: #E07A57; color-scheme: dark } }
:root[data-theme="dark"] {
  --bg: #1C1B19; --wash: #22211E; --ink: #EDEBE4; --ink-soft: #ADABA1; --ink-grey: #6F6D65;
  --hairline: #34322E; --edge: #3A3833; --clay: #E07A57; color-scheme: dark }
body { background: var(--bg); color: var(--ink); font-family: var(--sans); font-size: 15px; line-height: 1.55; }
.band { padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }
.band > div { max-width: 860px; margin: 0 auto; }
.top { background: var(--wash); border-bottom: 1px solid var(--edge); padding-block: 40px 32px; }
.bottom { background: var(--bg); padding-block: 32px 48px; }
.date { color: var(--ink-soft); font-size: 13px; letter-spacing: .02em; margin: 0 0 10px; }
h1 { font-family: var(--serif); font-weight: 600; font-size: 38px; line-height: 1.18; margin: 0; text-wrap: balance; max-width: 30ch; }
.rule { height: 2px; width: 56px; background: var(--clay); margin: 22px 0 26px; border-radius: 1px; }
.acts { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.act { padding: 0 20px; border-left: 1px solid var(--hairline); min-width: 0; }
.act:first-child { padding-left: 0; border-left: 0; }
.act b { display: block; font-size: 14px; margin-bottom: 4px; }
.act p { margin: 0; color: var(--ink-soft); font-size: 14px; }
section { margin-top: 30px; }
section:first-child { margin-top: 0; }
h2 { font-family: var(--sans); font-size: 13px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-soft); margin: 0 0 12px; }
ol { list-style: none; padding: 0; margin: 0; counter-reset: n; display: grid; gap: 14px; }
ol li { counter-increment: n; display: grid; grid-template-columns: 26px minmax(0, 1fr); }
ol li::before { content: counter(n); color: var(--ink-grey); font-variant-numeric: tabular-nums; font-size: 13px; padding-top: 2px; }
li > div { min-width: 0; overflow-wrap: anywhere; }
li strong { color: var(--ink); font-weight: 600; }
li .rest { color: var(--ink-soft); }
li.done .rest, li.done strong { text-decoration: line-through; text-decoration-color: var(--ink-grey); }
p.note { color: var(--ink-soft); margin: 0 0 10px; max-width: 65ch; }
a { color: inherit; text-decoration: underline; text-decoration-color: var(--ink-grey); text-underline-offset: 2px; }
a:hover { text-decoration-color: var(--clay); }
a:focus-visible { outline: 2px solid var(--clay); outline-offset: 2px; }
code { font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 12.5px; background: var(--wash); padding: 1px 4px; border-radius: 3px; }
.foot { margin-top: 12px; color: var(--ink-grey); font-size: 12px; }
section + .foot { margin-top: 36px; }
@media (max-width: 640px) {
  h1 { font-size: 29px; }
  .acts { grid-template-columns: minmax(0, 1fr); gap: 14px; }
  .act { padding: 14px 0 0; border-left: 0; border-top: 1px solid var(--hairline); }
  .act:first-child { padding-top: 0; border-top: 0; }
}
"""


def inline(text, vault):
    """Inline markdown to HTML: wikilinks, links, bold, code. Everything else is escaped."""
    out, pos = [], 0
    rx = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]+))?\]\]|\[([^\]]+)\]\((https?://[^)\s]+)\)|\*\*(.+?)\*\*|`([^`]+)`")
    for m in rx.finditer(text):
        out.append(html.escape(text[pos:m.start()]))
        if m.group(1):
            path, label = m.group(1).strip(), (m.group(2) or os.path.basename(m.group(1))).strip()
            uri = "obsidian://open?vault=" + urllib.parse.quote(vault) + "&file=" + urllib.parse.quote(path)
            out.append(f'<a href="{html.escape(uri)}">{html.escape(label)}</a>')
        elif m.group(3):
            out.append(f'<a href="{html.escape(m.group(4))}" target="_blank" rel="noopener">{html.escape(m.group(3))}</a>')
        elif m.group(5):
            out.append(f"<strong>{inline(m.group(5), vault)}</strong>")
        else:
            out.append(f"<code>{html.escape(m.group(6))}</code>")
        pos = m.end()
    out.append(html.escape(text[pos:]))
    return "".join(out)


def parse(body):
    """(title, headline, [(section, [paragraphs], [items], [(sub, text)])], [closing lines]).

    Lines after a `---` rule in the body close the briefing (the previous briefing's
    link, the agenda reminder) and are laid out small, at the very end of the page."""
    title, headline, sections, cur, tail = "", "", [], None, None
    for raw in body.split("\n"):
        ln = raw.rstrip()
        if tail is not None:
            if ln.strip():
                tail.append(ln.strip())
        elif ln.strip() == "---":
            tail = []
        elif ln.startswith("# ") and not title:
            title = ln[2:].strip()
        elif ln.startswith("## "):
            cur = [ln[3:].strip(), [], [], []]
            sections.append(cur)
        elif ln.startswith("### ") and cur is not None:
            cur[3].append([ln[4:].strip(), ""])
        elif re.match(r"^\s*[-*] ", ln) and cur is not None:
            if re.match(r"^\s{2,}", ln) and cur[2]:
                cur[2][-1] += " " + ln.strip()[2:]
            else:
                cur[2].append(ln.strip()[2:])
        elif ln.strip() and not ln.startswith(">") and not ln.startswith("<!--"):
            if cur is None:
                headline = (headline + " " + ln.strip()).strip()
            elif cur[3] and not cur[3][-1][1]:
                cur[3][-1][1] = ln.strip()
            else:
                cur[1].append(ln.strip())
    return title, headline, sections, tail or []


def item(text, vault):
    done = False
    m = re.match(r"^\[( |x|X)\]\s+(.*)$", text)
    if m:
        done, text = m.group(1) in "xX", m.group(2)
    m = re.match(r"^(\*\*.+?\*\*)\s*(.*)$", text)
    inner = f"{inline(m.group(1), vault)} <span class=\"rest\">{inline(m.group(2), vault)}</span>" if m else \
        f'<span class="rest">{inline(text, vault)}</span>'
    return f'<li{" class=\"done\"" if done else ""}><div>{inner}</div></li>'


def heading(root, path):
    """A briefing's own `# ` heading (its date), else its file name."""
    try:
        for ln in open(os.path.join(root, path), encoding="utf-8"):
            if ln.startswith("# "):
                return ln[2:].strip()
    except OSError:
        pass
    return os.path.basename(path)[:-3]


def write_index(root, files):
    """The index note: today's briefing, then every earlier one. Returns True if it changed."""
    link = lambda p: f"[[{p[:-3]}|{heading(root, p)}]]"
    lines = fm_block(type='"[[hub]]"', status='"#current"', generated_by="augment/render_briefing.py",
                     generated_at=stamp()) + [
        "# briefing", "",
        "The morning briefings, newest first, one note per briefing morning (skills/brief). Generated; do not edit by hand.", "",
        f"Latest: {link(files[0])}", ""]
    if len(files) > 1:
        lines += ["## Earlier", ""] + [f"- {link(p)}" for p in files[1:]] + [""]
    return write_if_changed(os.path.join(root, VIEW), "\n".join(lines))


def render(root, cfg, path, files):
    b = cfg.get("briefing") or {}
    vault = str(b.get("obsidian_vault") or os.path.basename(root.rstrip("/")))
    page_title = str(b.get("title") or "Morning Briefing")
    fm, body = split_note(open(os.path.join(root, path), encoding="utf-8").read())
    title, headline, sections, tail = parse(body)
    acts, lists = [], []
    for name, paras, items, subs in sections:
        if subs and not acts:            # the first section with ### subsections is the project strip
            acts = subs[:3]
            rest = subs[3:]
            if rest or items:
                lists.append((name, [], [f"**{s}** {t}" for s, t in rest] + items))
            continue
        lists.append((name, paras, items + [f"**{s}** {t}" for s, t in subs]))
    out = [f"<title>{html.escape(page_title)}</title>",
           '<meta name="claude:viewport-fit-sides" content="cover">',
           '<link rel="preconnect" href="https://fonts.googleapis.com">',
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&display=swap">',
           f"<style>{CSS}</style>",
           '<header class="band top"><div>',
           f'<p class="date">{html.escape(title)}</p>',
           f"<h1>{inline(headline or title, vault)}</h1>"]
    if acts:
        out.append('<div class="rule"></div><div class="acts">')
        for s, t in acts:
            out.append(f'<div class="act"><b>{inline(s, vault)}</b><p>{inline(t, vault)}</p></div>')
        out.append("</div>")
    out.append('</div></header><main class="band bottom"><div>')
    for name, paras, items in lists:
        if not paras and not items:
            continue
        out.append(f"<section><h2>{html.escape(name)}</h2>")
        out += [f'<p class="note">{inline(p, vault)}</p>' for p in paras]
        if items:
            out.append("<ol>" + "".join(item(i, vault) for i in items) + "</ol>")
        out.append("</section>")
    def when(v):
        try:
            return datetime.datetime.fromisoformat(str(v)).strftime("%-d %b %H:%M")
        except ValueError:
            return str(v)
    w = f"{when(fm.get('window_since', ''))} to {when(fm.get('window_until', ''))}"
    out += [f'<p class="foot">{inline(t, vault)}</p>' for t in tail]
    out.append(f'<p class="foot">From the vault at {html.escape(str(fm.get("vault_commit", "")))}, covering {html.escape(w)}.</p>')
    earlier = [p for p in files if p != path][:EARLIER]
    if earlier:
        out.append('<p class="foot">Earlier briefings: ' + ", ".join(
            inline(f"[[{p[:-3]}|{heading(root, p)}]]", vault) for p in earlier) + ".</p>")
    out.append("</div></main>")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("vault")
    ap.add_argument("--file", help="a dated briefing to lay out instead of the newest")
    ap.add_argument("--out")
    a = ap.parse_args()
    root = os.path.abspath(a.vault)
    files = dated(root)
    path = a.file or (files[0] if files else None)
    if not path or not os.path.exists(os.path.join(root, path)):
        print(f"REFUSED: no briefing in {DATED}/; write one first (skills/brief)")
        sys.exit(1)
    out = a.out or os.path.join(tempfile.gettempdir(), "augment-scratch", "briefing.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8", newline="\n").write(render(root, load_config(root), path, files))
    changed = write_index(root, files)
    print(out)
    print(f"index {VIEW} {'rewritten' if changed else 'unchanged'}, {len(files)} briefing(s)")


if __name__ == "__main__":
    main()
