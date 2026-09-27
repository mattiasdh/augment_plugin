/**
 * The memory layer over the connector: the rules of the plugin's
 * `reference/memory.md`, ported from `scripts/_memory.py` and `memory_write.py`
 * so a card written here is byte-for-byte the card the Python writer would have
 * written, and a duplicate is refused on the same measure. The test suite holds
 * the two to each other.
 */
import { parse as parseYaml } from "yaml";
import type { Repo, RepoFile } from "./github";

export const DIR = "augment_memory";
export const CARD_DIR = `${DIR}/card`;
export const OFFER_DIR = `${DIR}/offers`;
export const TYPES = ["preference", "procedure", "tool", "snippet"] as const;
export type CardType = (typeof TYPES)[number];
const ORDER = ["type", "title", "summary", "status", "superseded_by", "scope", "keywords",
  "seen", "created", "updated", "by"];
export const SUMMARY_MAX = 160;
export const TITLE_WORDS = 10;
export const SAME = 0.5;

export const DEFAULTS = { enabled: true, index_cap: 150, inject_chars: 6000, decay_days: 180 };
export type MemorySettings = typeof DEFAULTS;

const STOP = new Set(`a an and are as at be but by can do does for from has have how if in into is it its
not of on or so that the their then there these this to use used uses using was were what when
which while will with without you your via per than also only just more most such`.split(/\s+/));

const SECRET: RegExp[] = [
  /ghp_[A-Za-z0-9]{20,}/,
  /github_pat_[A-Za-z0-9_]{20,}/,
  /\bsk-[A-Za-z0-9_\-]{20,}/,
  /\bAKIA[0-9A-Z]{16}\b/,
  /xox[baprs]-[A-Za-z0-9\-]{10,}/,
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
  /\b(password|passwd|secret|api[_-]?key|access[_-]?token|token)\b\s*[:=]\s*["']?[A-Za-z0-9_\-./+]{12,}/i,
];

export class Refused extends Error {}

export type Front = Record<string, unknown>;
export interface Card { slug: string; sha: string; fm: Front; body: string }

// ---- the card model, as in _memory.py ----

const FM = /^---\n([\s\S]*?)\n---\n?/;

export function splitNote(text: string): [Front, string] {
  const m = FM.exec(text || "");
  if (!m) return [{}, text || ""];
  let fm: unknown;
  try { fm = parseYaml(m[1]); } catch { fm = {}; }
  return [fm && typeof fm === "object" && !Array.isArray(fm) ? (fm as Front) : {}, text.slice(m[0].length)];
}

export function slugify(title: string): string {
  const s = title.normalize("NFKD").replace(/[^\x00-\x7f]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return s.slice(0, 70).replace(/-+$/, "") || "memory";
}

export function tokens(text: unknown): Set<string> {
  const out = new Set<string>();
  const words = String(text ?? "").normalize("NFKD").toLowerCase().match(/[a-z0-9][a-z0-9_\-]{1,}/g) || [];
  for (const w of words) {
    for (const part of [...w.split(/[_\-]/), w]) {
      if (part.length >= 3 && !STOP.has(part)) out.add(part.endsWith("s") && part.length > 4 ? part.slice(0, -1) : part);
    }
  }
  return out;
}

export function asList(v: unknown): string[] {
  if (v === null || v === undefined || v === "") return [];
  return Array.isArray(v) ? v.map(String) : [String(v)];
}

export function cardTokens(fm: Front): Set<string> {
  return tokens([String(fm.title ?? ""), String(fm.summary ?? ""), asList(fm.keywords).join(" ")].join(" "));
}

export function jaccard(a: Set<string>, b: Set<string>): number {
  if (!a.size || !b.size) return 0;
  let inter = 0;
  for (const x of a) if (b.has(x)) inter++;
  return inter / (a.size + b.size - inter);
}

export function scopes(fm: Front): string[] {
  const s = asList(fm.scope).map((x) => x.toLowerCase());
  return s.length ? s : ["global"];
}

export function seenOf(fm: Front): number {
  const n = parseInt(String(fm.seen ?? "1"), 10);
  return Number.isFinite(n) && n > 0 ? n : 1;
}

export function sortCards(cards: Card[]): Card[] {
  const byType = new Map<string, number>(TYPES.map((t, i) => [t, i]));
  const out = [...cards].sort((a, b) => (a.slug < b.slug ? -1 : a.slug > b.slug ? 1 : 0));
  out.sort((a, b) => { const x = String(a.fm.updated ?? ""), y = String(b.fm.updated ?? ""); return x < y ? 1 : x > y ? -1 : 0; });
  out.sort((a, b) => seenOf(b.fm) - seenOf(a.fm));
  out.sort((a, b) => (byType.get(String(a.fm.type)) ?? 99) - (byType.get(String(b.fm.type)) ?? 99));
  return out;
}

export function secretIn(text: string): string | null {
  for (const rx of SECRET) {
    const m = rx.exec(text || "");
    if (m) return m[0].slice(0, 12) + "...";
  }
  return null;
}

/** A YAML double-quoted scalar, as Python's json.dumps(ensure_ascii=False) writes it. */
export function q(v: unknown): string {
  return JSON.stringify(String(v));
}

export function render(fm: Front, body: string): string {
  const lines = ["---"];
  for (const k of ORDER) {
    const v = fm[k];
    if (v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0)) continue;
    if (k === "title" || k === "summary") lines.push(`${k}: ${q(v)}`);
    else if (k === "keywords") lines.push(`keywords: [${asList(v).map(q).join(", ")}]`);
    else if (k === "scope") {
      const sc = asList(v);
      lines.push(sc.length === 1 ? `scope: ${sc[0]}` : `scope: [${sc.map(q).join(", ")}]`);
    } else lines.push(`${k}: ${v}`);
  }
  lines.push("---");
  return lines.join("\n") + "\n" + body.replace(/^\n+|\n+$/g, "") + "\n";
}

export function indexLine(c: Card): string {
  const sc = asList(c.fm.scope);
  return `- [${c.fm.type ?? "?"}] [[${c.slug}]] (${(sc.length ? sc : ["global"]).join(", ")}): ${c.fm.summary ?? ""}`;
}

export function settingsFrom(config: Record<string, unknown>): MemorySettings {
  const m = (config.memory ?? {}) as Partial<MemorySettings>;
  return {
    enabled: m.enabled ?? DEFAULTS.enabled,
    index_cap: Number(m.index_cap ?? DEFAULTS.index_cap),
    inject_chars: Number(m.inject_chars ?? DEFAULTS.inject_chars),
    decay_days: Number(m.decay_days ?? DEFAULTS.decay_days),
  };
}

function toCard(f: RepoFile): Card {
  const [fm, body] = splitNote(f.text);
  return { slug: f.path.split("/").pop()!.replace(/\.md$/, ""), sha: f.sha, fm, body };
}

const isActive = (c: Card) => String(c.fm.status ?? "active") === "active";

// ---- checks, as memory_write.py makes them ----

function checkFields(title?: string, summary?: string, type?: string) {
  if (title !== undefined) {
    if (!title.trim()) throw new Refused("empty title");
    const n = title.trim().split(/\s+/).length;
    if (n > TITLE_WORDS) throw new Refused(`title has ${n} words; ten at most`);
  }
  if (summary !== undefined) {
    if (!summary.trim() || summary.includes("\n")) throw new Refused("the summary is one non-empty line");
    if (summary.length > SUMMARY_MAX) throw new Refused(`summary is ${summary.length} characters; ${SUMMARY_MAX} at most`);
  }
  if (type !== undefined && !(TYPES as readonly string[]).includes(type)) throw new Refused(`type must be one of ${TYPES.join(", ")}`);
}

function checkSecret(...texts: (string | undefined)[]) {
  for (const t of texts) {
    const hit = secretIn(t ?? "");
    if (hit) throw new Refused(`this looks like a secret (${hit}). Memory never holds credentials; describe where the secret lives instead, and do not reformat it to get past this check.`);
  }
}

function checkSlug(slug: string) {
  if (!/^[a-z0-9][a-z0-9-]*$/.test(slug)) throw new Refused(`${slug} is not a card slug`);
}

function splitCsv(v: string | string[] | undefined): string[] {
  if (Array.isArray(v)) return v.map((x) => String(x).trim()).filter(Boolean);
  return (v ?? "").split(",").map((x) => x.trim()).filter(Boolean);
}

// ---- the operations ----

export class Memory {
  constructor(private repo: Repo, private settings: MemorySettings, private now: () => string, private by: string) {}

  async cards(): Promise<Card[]> {
    return (await this.repo.readDir(CARD_DIR)).map(toCard);
  }

  private guard() {
    if (!this.settings.enabled) throw new Refused("memory is disabled in this vault's config.yaml (memory.enabled: false)");
  }

  /** The session-start context, as memory_context.py builds it. */
  async context(project: string): Promise<string> {
    const p = project.toLowerCase();
    const active = (await this.cards()).filter(isActive);
    const mine = active.filter((c) => scopes(c.fm).includes(p));
    const general = active.filter((c) => scopes(c.fm).includes("global") && !mine.includes(c));
    const total = mine.length + general.length;
    if (!total) return `AUGMENT MEMORY: no cards apply${p ? ` to ${p}` : ""} yet.`;
    const out = [`AUGMENT MEMORY: ${total} card${total === 1 ? "" : "s"} for this session (${mine.length} scoped to ${p || "no project"}, ${general.length} global). One line each; memory_get holds the detail and memory_search finds the rest. Memory says how to work, never what is true about the domain.`];
    let used = 0, left = 0;
    for (const c of [...sortCards(mine), ...sortCards(general)]) {
      const line = indexLine(c);
      if (used + line.length > this.settings.inject_chars) { left++; continue; }
      out.push(line);
      used += line.length + 1;
    }
    if (left) out.push(`(${left} more past the ${this.settings.inject_chars}-character budget; memory_search finds them.)`);
    return out.join("\n");
  }

  async search(query: string, opts: { type?: string; scope?: string; all?: boolean; limit?: number } = {}): Promise<string> {
    const qt = tokens(query);
    if (!qt.size) throw new Refused("no searchable words in the query");
    const hits: [number, number, Card][] = [];
    for (const c of await this.cards()) {
      if (!opts.all && !isActive(c)) continue;
      if (opts.type && c.fm.type !== opts.type) continue;
      if (opts.scope && !scopes(c.fm).includes(opts.scope.toLowerCase()) && !scopes(c.fm).includes("global")) continue;
      const title = new Set([...tokens(c.fm.title ?? ""), ...tokens(asList(c.fm.keywords).join(" "))]);
      const summary = tokens(c.fm.summary ?? "");
      const rest = tokens(c.body);
      let s = 0;
      for (const t of qt) s += 3 * +title.has(t) + 2 * +summary.has(t) + +rest.has(t);
      if (s) hits.push([s, seenOf(c.fm), c]);
    }
    hits.sort((a, b) => b[0] - a[0] || b[1] - a[1] || (a[2].slug < b[2].slug ? -1 : 1));
    if (!hits.length) return `no card matches: ${[...qt].sort().join(" ")}`;
    const limit = opts.limit ?? 10;
    const lines = hits.slice(0, limit).map(([s, , c]) => {
      let flag = isActive(c) ? "" : ` ${String(c.fm.status).toUpperCase()}`;
      if (c.fm.superseded_by) flag += ` -> ${c.fm.superseded_by}`;
      return `${String(s).padStart(3)}  ${c.slug}  [${c.fm.type}, ${scopes(c.fm).join(", ")}]${flag}  ${c.fm.summary ?? ""}`;
    });
    if (hits.length > limit) lines.push(`... ${hits.length - limit} more; narrow the query`);
    return lines.join("\n");
  }

  async get(slug: string): Promise<string> {
    checkSlug(slug);
    const f = await this.repo.read(`${CARD_DIR}/${slug}.md`);
    if (!f) throw new Refused(`no card ${slug}`);
    return f.text;
  }

  async add(a: { type: string; title: string; summary: string; scope?: string | string[]; keywords?: string | string[]; body?: string; distinct?: boolean }): Promise<string> {
    this.guard();
    const body = a.body ?? "";
    checkFields(a.title, a.summary, a.type);
    checkSecret(a.title, a.summary, splitCsv(a.keywords).join(","), body);
    const now = this.now();
    const scope = splitCsv(a.scope);
    const fm: Front = { type: a.type, title: a.title.trim(), summary: a.summary.trim(), status: "active",
      scope: scope.length ? scope : ["global"], keywords: splitCsv(a.keywords), seen: 1, created: now, updated: now, by: this.by };
    const cards = await this.cards();
    if (!a.distinct) {
      const mine = cardTokens(fm);
      let best: [number, string] = [0, ""];
      for (const c of cards) if (isActive(c)) {
        const j = jaccard(mine, cardTokens(c.fm));
        if (j > best[0]) best = [j, c.slug];
      }
      if (best[0] >= SAME) throw new Refused(`LIKELY SAME as active card ${best[1]} (${best[0].toFixed(2)}). Confirm it with memory_seen, amend it with memory_update, or pass distinct only if the two really differ.`);
    }
    const slug = slugify(a.title);
    if (cards.some((c) => c.slug === slug)) throw new Refused(`a card named ${slug} exists already; update it, or choose a title that says what differs`);
    const r = await this.repo.write(`${CARD_DIR}/${slug}.md`, render(fm, body), `MEMORY: add ${slug}\n\nAssisted-by: ${this.by}`);
    if (r !== "ok") throw new Refused(`a card named ${slug} appeared meanwhile; search again`);
    return `added ${CARD_DIR}/${slug}.md (${a.type}, ${(fm.scope as string[]).join(", ")})`;
  }

  private async edit(slug: string, change: (fm: Front, body: string) => [Front, string], verb: string): Promise<void> {
    this.guard();
    checkSlug(slug);
    const path = `${CARD_DIR}/${slug}.md`;
    for (let attempt = 0; attempt < 2; attempt++) {
      const f = await this.repo.read(path);
      if (!f) throw new Refused(`no card ${slug}`);
      const [fm, body] = splitNote(f.text);
      const [nfm, nbody] = change(fm, body);
      const r = await this.repo.write(path, render(nfm, nbody), `MEMORY: ${verb} ${slug}\n\nAssisted-by: ${this.by}`, f.sha);
      if (r === "ok") return;
    }
    throw new Refused(`${slug} kept changing underneath this write; try again`);
  }

  async seen(slug: string): Promise<string> {
    let n = 0;
    await this.edit(slug, (fm, body) => { n = seenOf(fm) + 1; return [{ ...fm, seen: n, updated: this.now() }, body]; }, "seen");
    return `${slug}: seen ${n}`;
  }

  async update(slug: string, a: { title?: string; summary?: string; type?: string; scope?: string | string[]; keywords?: string | string[]; body?: string }): Promise<string> {
    checkFields(a.title, a.summary, a.type);
    checkSecret(a.title, a.summary, splitCsv(a.keywords).join(","), a.body);
    await this.edit(slug, (fm, body) => {
      const n: Front = { ...fm };
      for (const k of ["title", "summary", "type"] as const) if (a[k] !== undefined) n[k] = a[k]!.trim();
      if (a.scope !== undefined) { const s = splitCsv(a.scope); n.scope = s.length ? s : ["global"]; }
      if (a.keywords !== undefined) n.keywords = splitCsv(a.keywords);
      n.updated = this.now();
      return [n, a.body === undefined ? body : a.body];
    }, "update");
    return `updated ${CARD_DIR}/${slug}.md`;
  }

  async supersede(oldSlug: string, newSlug: string): Promise<string> {
    if (oldSlug === newSlug) throw new Refused("a card cannot supersede itself");
    checkSlug(newSlug);
    if (!(await this.repo.read(`${CARD_DIR}/${newSlug}.md`))) throw new Refused(`no card ${newSlug}`);
    await this.edit(oldSlug, (fm, body) => [{ ...fm, status: "superseded", superseded_by: newSlug, updated: this.now() }, body], "supersede");
    return `${oldSlug} superseded by ${newSlug}`;
  }

  async offer(a: { title: string; body: string; kind?: string; target?: string }): Promise<string> {
    this.guard();
    if (!a.body?.trim()) throw new Refused("an offer needs the drafted content as its body");
    checkFields(a.title);
    checkSecret(a.title, a.body);
    const now = this.now();
    const slug = `${now.slice(0, 10)}-${slugify(a.title)}`;
    const extra = [a.kind && a.kind !== "capture" ? `kind: ${a.kind}` : "", a.target ? `target: ${q(a.target)}` : ""].filter(Boolean);
    const text = ["---", `title: ${q(a.title.trim())}`, `offered: ${now}`, ...extra, `assisted_by: ${this.by}`, "---"].join("\n") + "\n" + a.body.trim() + "\n";
    const r = await this.repo.write(`${OFFER_DIR}/${slug}.md`, text, `MEMORY: offer ${slug}\n\nAssisted-by: ${this.by}`);
    if (r !== "ok") throw new Refused(`an offer ${slug} exists already`);
    return `offered ${OFFER_DIR}/${slug}.md; the weekly sweep moves it into the source layer through write`;
  }
}
