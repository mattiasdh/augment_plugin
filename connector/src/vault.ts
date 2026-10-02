/**
 * The vault beyond memory: search, reading, and capture into the inbox (the other writes are in write.ts).
 *
 * What may be read is decided by the vault's own `augment_wiki/config.yaml`, read
 * at request time and never restated here: a source is readable when the scope
 * rules put it in scope (the plugin's `_gen_util.scope_of`, ported) and it does
 * not carry `#excluded`. The wiki and the memory layer are readable whole, since
 * both are written by the system from what scope already allowed. The only write
 * here is a new file in the inbox; changes to existing files go through write.ts, under the rules of the
 * plugin's rules/surfaces.md, so the person's text is never rewritten on any surface
 * (source_write.py is ported for the two writes a source takes).
 */
import { parse as parseYaml } from "yaml";
import type { Repo } from "./github";
import { Refused, splitNote, tokens } from "./memory";

export type Config = Record<string, unknown>;
interface Rule { path?: string; in_scope?: boolean }
interface Entry { id: string; title?: string; type?: string; kind?: string; status?: string; renamed_to?: string; deleted?: unknown; produced?: string[] }

const TTL_MS = 300_000;  // five minutes: fewer cold loads, and a scope change still arrives within minutes
const cache = new Map<string, { at: number; value: unknown }>();

async function cached<T>(key: string, load: () => Promise<T>): Promise<T> {
  const hit = cache.get(key);
  if (hit && Date.now() - hit.at < TTL_MS) return hit.value as T;
  const value = await load();
  cache.set(key, { at: Date.now(), value });
  return value;
}

export function clearCache() { cache.clear(); }

/**
 * The top-level sections of config.yaml the connector reads, and nothing else. The
 * file is mostly commentary and declarations the connector never uses, and parsing
 * all of it took more than half of a cold request's CPU on the free plan. A section
 * starts at a key in column 0 and runs to the next; a column-0 comment is dropped,
 * which is safe because YAML indents every line of a block scalar.
 */
const CONFIG_SECTIONS = ["scope", "source_root", "memory", "skills", "author"];

export function configSections(text: string, keep = CONFIG_SECTIONS): string {
  const out: string[] = [];
  let on = false;
  for (const line of text.split("\n")) {
    const m = /^([A-Za-z_][\w-]*):/.exec(line);
    if (m) on = keep.includes(m[1]);
    else if (line.startsWith("#")) continue;
    if (on) out.push(line);
  }
  return out.join("\n");
}

export async function loadConfig(repo: Repo, key = ""): Promise<Config> {
  return cached(`config:${key}`, async () => {
    const f = await repo.read("augment_wiki/config.yaml");
    if (!f) throw new Refused("no augment_wiki/config.yaml in the repository; this is not an augment vault");
    const c = parseYaml(configSections(f.text));
    return c && typeof c === "object" ? (c as Config) : {};
  });
}

async function loadIndex(repo: Repo, key = ""): Promise<Entry[]> {
  return cached(`index:${key}`, async () => {
    const f = await repo.read("augment_wiki/index.jsonl");
    if (!f) return [];
    const out: Entry[] = [];
    for (const line of f.text.split("\n")) {
      if (!line.trim()) continue;
      try { out.push(JSON.parse(line)); } catch { /* a torn line is skipped, not fatal */ }
    }
    return out;
  });
}

/** `ignore`, `in`, `out` or `undecided`, exactly as `_gen_util.scope_of` decides. */
export function scopeOf(path: string, config: Config): "ignore" | "in" | "out" | "undecided" {
  const sc = (config.scope ?? {}) as { ignore?: string[]; rules?: Rule[] };
  for (const ig of sc.ignore ?? []) {
    if (path === ig || path.startsWith(String(ig).replace(/\/+$/, "") + "/")) return "ignore";
  }
  let best: Rule | null = null;
  for (const r of sc.rules ?? []) {
    const d = String(r.path ?? "");
    if ((path === d || path.startsWith(d + "/")) && (best === null || d.length > String(best.path ?? "").length)) best = r;
  }
  if (best === null) return "undecided";
  return best.in_scope ? "in" : "out";
}

export function cleanPath(path: string): string {
  const p = String(path || "").trim().replace(/^\/+/, "");
  if (!p || p.split("/").some((s) => s === ".." || s === "." || s === "") || p.startsWith(".")) {
    throw new Refused(`${path} is not a vault path`);
  }
  return p;
}

const WHY: Record<string, string> = {
  ignore: "is in a folder the vault's config.yaml ignores (scratch, staging or infrastructure)",
  out: "is in a folder the vault's config.yaml rules out of scope",
  undecided: "is in a folder the vault's config.yaml has not ruled on yet, and an unruled folder stays closed",
};

/** The skills root config.yaml declares (`skills: root:`), or "" when none is. */
export function skillsRoot(config: Config): string {
  const r = String(((config.skills ?? {}) as { root?: string }).root ?? "").trim().replace(/^\/+|\/+$/g, "");
  return r && !r.split("/").some((x) => x === ".." || x === ".") ? r : "";
}

export async function read(repo: Repo, path: string): Promise<string> {
  const p = cleanPath(path);
  if (!p.endsWith(".md")) throw new Refused("only markdown notes are readable through the connector");
  let system = p.startsWith("augment_wiki/") || p.startsWith("augment_memory/");
  if (!system) {
    const root = skillsRoot(await loadConfig(repo));
    // A skill's own files are method, not knowledge: out of the wiki's scope, yet read on every use of the skill.
    system = root !== "" && p.startsWith(root + "/");
  }
  if (!system) {
    const config = await loadConfig(repo);
    const s = scopeOf(p, config);
    if (s !== "in") throw new Refused(`${p} ${WHY[s]}`);
    const e = (await loadIndex(repo)).find((x) => x.id === p);
    if (e?.status === "excluded") throw new Refused(`${p} is declared #excluded`);
  }
  const f = await repo.read(p);
  if (!f) throw new Refused(`no note at ${p}`);
  if (!system) {
    const [fm] = splitNote(f.text);
    if (String(fm.augment ?? "").includes("#excluded")) throw new Refused(`${p} is declared #excluded`);
  }
  return f.text;
}

interface SearchNote { id: string; title?: string; type?: string; kind?: string; status?: string; aliases?: string[]; keywords?: string[]; summary?: string; sources?: string[];
  w?: Record<string, number>; d?: string[] }
interface SearchSource { id: string; cited_by?: string[]; t?: string[]; n?: string[] }
interface SearchIndex { notes: SearchNote[]; sources: SearchSource[] }
interface Prepared {
  notes: { n: SearchNote; weight: Map<string, number>; named: Set<string> }[];
  sources: { s: SearchSource; words: Set<string>; name: Set<string> }[];
}

/** A note's word weights (title and aliases 3, keywords 2, summary 1), as gen_search.py writes them into `w`. */
function weigh(n: SearchNote): { weight: Map<string, number>; named: Set<string> } {
  if (n.w && n.d) return { weight: new Map(Object.entries(n.w)), named: new Set(n.d) };
  const named = new Set([...tokens(`${n.title ?? ""} ${n.id.split("/").pop()}`), ...tokens((n.aliases ?? []).join(" "))]);
  const weight = new Map<string, number>();
  for (const t of tokens(n.summary ?? "")) weight.set(t, 1);
  for (const t of tokens((n.keywords ?? []).join(" "))) weight.set(t, 2);
  for (const t of named) weight.set(t, 3);
  return { weight, named };
}

/**
 * augment_wiki/search.json, written by the plugin's gen_search.py, tokenised once when
 * loaded so a query costs only set lookups: the free plan allows 10 ms of CPU a
 * request, and re-tokenising every note per query took twice that. Null on a vault
 * that has no search.json yet.
 */
async function loadSearch(repo: Repo, key = ""): Promise<Prepared | null> {
  return cached(`search:${key}`, async () => {
    const f = await repo.read("augment_wiki/search.json");
    if (!f) return null;
    let d: SearchIndex;
    try {
      d = JSON.parse(f.text) as SearchIndex;
    } catch {
      return null;
    }
    if (!Array.isArray(d.notes) || !Array.isArray(d.sources)) return null;
    return {
      notes: d.notes.map((n) => ({ n, ...weigh(n) })),
      sources: d.sources.map((s) => ({
        s,
        words: s.t ? new Set(s.t) : tokens(s.id.replace(/\.md$/, "")),
        name: s.n ? new Set(s.n) : tokens(s.id.split("/").pop()!.replace(/\.md$/, "")),
      })),
    };
  });
}

/** Per query word, the strongest field it appears in. */
function scoreNote(qt: Set<string>, p: Prepared["notes"][number]): number {
  let s = 0;
  for (const t of qt) s += p.weight.get(t) ?? 0;
  return s;
}

export async function search(repo: Repo, query: string, opts: { limit?: number; sources?: boolean } = {}): Promise<string> {
  const idx = await loadSearch(repo);
  if (!idx) return searchIndexOnly(repo, query, opts);
  const qt = tokens(query);
  if (!qt.size) throw new Refused("no searchable words in the query");
  const config = await loadConfig(repo);
  const hits: [number, number, string][] = [];
  for (const p of idx.notes) {
    const s = scoreNote(qt, p);
    if (!s) continue;
    const n = p.n;
    const al = n.aliases?.length ? `  (also: ${n.aliases.join(", ")})` : "";
    hits.push([s, 1, `${n.id}  [${n.type ?? "note"}${n.kind ? ` ${n.kind}` : ""}, ${n.status ?? ""}] ${n.title ?? ""}${al}`]);
  }
  if (opts.sources !== false) {
    for (const { s: src, words } of idx.sources) {
      let s = 0;
      for (const t of qt) s += +words.has(t);
      if (s && scopeOf(src.id, config) === "in") hits.push([s, 0, `${src.id}  [source, cited by ${(src.cited_by ?? []).length} note(s)]`]);
    }
  }
  hits.sort((a, b) => b[0] - a[0] || b[1] - a[1] || (a[2] < b[2] ? -1 : 1));
  if (!hits.length) return `nothing matches: ${[...qt].sort().join(" ")}. Titles, aliases, keywords, summaries and source paths were searched; try the names a note or its sources would use.`;
  const limit = opts.limit ?? 15;
  const lines = hits.slice(0, limit).map(([s, , l]) => `${String(s).padStart(3)}  ${l}`);
  if (hits.length > limit) lines.push(`... ${hits.length - limit} more; narrow the query`);
  return lines.join("\n");
}

/** Possible duplicates of a capture title, from search.json: a note or source carrying most of its words. */
export async function likelyDuplicates(repo: Repo, title: string): Promise<string[]> {
  const idx = await loadSearch(repo);
  const qt = tokens(title);
  if (!idx || qt.size < 2) return [];
  const config = await loadConfig(repo);
  const out: [number, string][] = [];
  const share = (words: Set<string>) => [...qt].filter((t) => words.has(t)).length / qt.size;
  for (const p of idx.notes) {
    const r = share(p.named);
    if (r >= 0.6) out.push([r, `${p.n.id} (${p.n.title ?? ""})`]);
  }
  for (const { s, name } of idx.sources) {
    const r = share(name);
    if (r >= 0.6 && scopeOf(s.id, config) === "in") out.push([r, s.id]);
  }
  return out.sort((a, b) => b[0] - a[0]).slice(0, 5).map(([, l]) => l);
}

/** The pre-search.json path: titles and paths from index.jsonl. */
async function searchIndexOnly(repo: Repo, query: string, opts: { limit?: number; sources?: boolean } = {}): Promise<string> {
  const qt = tokens(query);
  if (!qt.size) throw new Refused("no searchable words in the query");
  const [config, index] = [await loadConfig(repo), await loadIndex(repo)];
  const hits: [number, string][] = [];
  for (const e of index) {
    if (e.renamed_to || e.deleted) continue;
    const wiki = e.id.startsWith("augment_wiki/");
    if (!wiki) {
      if (opts.sources === false || e.status !== "processed" || scopeOf(e.id, config) !== "in") continue;
    }
    const words = wiki ? tokens(`${e.title ?? ""} ${e.id.split("/").pop()}`) : tokens(e.id.replace(/\.md$/, ""));
    let s = 0;
    for (const t of qt) s += +words.has(t);
    if (!s) continue;
    const label = wiki ? `[${e.type ?? "note"}${e.kind ? ` ${e.kind}` : ""}, ${e.status ?? ""}] ${e.title ?? ""}` : "[source]";
    hits.push([s * (wiki ? 2 : 1), `${e.id}  ${label}`]);
  }
  hits.sort((a, b) => b[0] - a[0] || (a[1] < b[1] ? -1 : 1));
  if (!hits.length) return `nothing in the index matches: ${[...qt].sort().join(" ")}. The index carries titles and paths only; try the names a note would use.`;
  const limit = opts.limit ?? 15;
  const lines = hits.slice(0, limit).map(([s, l]) => `${String(s).padStart(3)}  ${l}`);
  if (hits.length > limit) lines.push(`... ${hits.length - limit} more; narrow the query`);
  return lines.join("\n");
}

const UNSAFE = /[\\/:*?"<>|#^[\]\x00-\x1f]/g;

export async function capture(repo: Repo, a: { title: string; body: string; authorship: "model" | "person"; provenance?: string },
  now: string, by: string): Promise<string> {
  const title = String(a.title || "").trim();
  if (!title) throw new Refused("a captured note needs a title");
  if (!a.body?.trim()) throw new Refused("a captured note needs a body");
  const config = await loadConfig(repo);
  const root = String(config.source_root ?? "").replace(/^\/+|\/+$/g, "");
  const inbox = root ? `${root}/_inbox` : "_inbox";
  const name = title.replace(UNSAFE, " ").replace(/\s+/g, " ").trim().slice(0, 120);
  if (!name) throw new Refused("the title leaves no usable file name");
  const path = `${inbox}/${name}.md`;
  const fm = ["---", `augment: "#to-process"`, `created: ${now}`, `updated: ${now}`];
  let body = `# ${title}\n\n`;
  if (a.authorship === "model") {
    fm.push(`assisted_by: ${by}`);
    const why = (a.provenance || "Drafted in a Claude conversation and captured through the augment connector.").replace(/\s*\n\s*/g, " ").trim();
    body += `> [!ai] ${by}, ${now.slice(0, 10)}\n> ${why}\n\n`;
  }
  body += a.body.trim() + "\n";
  const text = fm.join("\n") + "\n---\n\n" + body;
  const r = await repo.write(path, text, `CAPTURE: ${name}\n\n${a.authorship === "model" ? `Assisted-by: ${by}\n` : ""}`);
  if (r !== "ok") throw new Refused(`${path} exists already; choose a title that says what differs`);
  const dup = await likelyDuplicates(repo, title);
  const warn = dup.length ? `\nPossible duplicates already in the vault: ${dup.join("; ")}. If one of them already holds this, tell the person, and prefer memory_offer with kind comment and that note as target next time.` : "";
  return `captured ${path}. It sits in the inbox, unaddressed and out of scope, until the person files it at the weekly sweep.${warn}`;
}

