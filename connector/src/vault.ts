/**
 * The vault beyond memory: search, reading, and capture into the inbox.
 *
 * What may be read is decided by the vault's own `augment_wiki/config.yaml`, read
 * at request time and never restated here: a source is readable when the scope
 * rules put it in scope (the plugin's `_gen_util.scope_of`, ported) and it does
 * not carry `#excluded`. The wiki and the memory layer are readable whole, since
 * both are written by the system from what scope already allowed. The only write
 * outside `augment_memory/` is a new file in the inbox; nothing existing in the
 * source layer is ever touched, which is what the method requires of a surface
 * that cannot run `source_write.py`.
 */
import { parse as parseYaml } from "yaml";
import type { Repo } from "./github";
import { Refused, splitNote, tokens } from "./memory";

export type Config = Record<string, unknown>;
interface Rule { path?: string; in_scope?: boolean }
interface Entry { id: string; title?: string; type?: string; kind?: string; status?: string; renamed_to?: string; deleted?: unknown; produced?: string[] }

const TTL_MS = 60_000;
const cache = new Map<string, { at: number; value: unknown }>();

async function cached<T>(key: string, load: () => Promise<T>): Promise<T> {
  const hit = cache.get(key);
  if (hit && Date.now() - hit.at < TTL_MS) return hit.value as T;
  const value = await load();
  cache.set(key, { at: Date.now(), value });
  return value;
}

export function clearCache() { cache.clear(); }

export async function loadConfig(repo: Repo, key = ""): Promise<Config> {
  return cached(`config:${key}`, async () => {
    const f = await repo.read("augment_wiki/config.yaml");
    if (!f) throw new Refused("no augment_wiki/config.yaml in the repository; this is not an augment vault");
    const c = parseYaml(f.text);
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

export async function read(repo: Repo, path: string): Promise<string> {
  const p = cleanPath(path);
  if (!p.endsWith(".md")) throw new Refused("only markdown notes are readable through the connector");
  const system = p.startsWith("augment_wiki/") || p.startsWith("augment_memory/");
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

export async function search(repo: Repo, query: string, opts: { limit?: number; sources?: boolean } = {}): Promise<string> {
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
  return `captured ${path}. It sits in the inbox, unaddressed and out of scope, until the person files it at the weekly sweep.`;
}

