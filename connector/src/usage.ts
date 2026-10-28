/**
 * Usage, the connector's half of the plugin's `scripts/usage_log.py`: which wiki notes
 * and memory cards were opened through this connector, and which were cited or applied.
 *
 * Opens are frequent and one commit each would bury the history, so they wait in the
 * Worker's key-value store, one key per event (no read-modify-write, so no race). They
 * reach the vault as one file in `augment_wiki/usage.pending/`, committed when
 * `usage_cite` is called or at the next `activate`. The nightly cycle's
 * `compact_index.py` folds that file into `augment_wiki/usage.jsonl` and projects it
 * onto the index; nothing here writes a note, a card or the index.
 */
import type { Change, Repo } from "./github";
import { Refused } from "./memory";
import { loadConfig, skillsRoot, type Config } from "./vault";

/** The slice of Workers KV this needs; the tests supply an in-memory one. */
export interface UsageStore {
  put(key: string, value: string, opts?: { expirationTtl?: number }): Promise<void>;
  get(key: string): Promise<string | null>;
  delete(key: string): Promise<void>;
  list(opts: { prefix: string; cursor?: string }): Promise<{ keys: { name: string }[]; list_complete: boolean; cursor?: string }>;
}

const PREFIX = "usage:";
const KEEP_S = 60 * 24 * 3600;   // an event not flushed in sixty days lapses rather than piling up
const WIKI_DIRS = ["concept", "entity", "theme", "tension", "hub"];
export const PENDING = "augment_wiki/usage.pending";

/**
 * A wiki note, a memory card (in its type folder, or flat before 2026-10-28), or a
 * skill's MEMORY.md under the declared skills root: all that usage tracks.
 */
export function tracked(path: string, skillsRoot = ""): boolean {
  const p = path.split("/");
  if (!p[p.length - 1].endsWith(".md")) return false;
  if (p.length === 3 && p[0] === "augment_wiki" && WIKI_DIRS.includes(p[1])) return true;
  if (p[0] === "augment_memory" && p[1] === "card" && (p.length === 3 || p.length === 4)) return true;
  return !!skillsRoot && p.length === skillsRoot.split("/").length + 2 && path.startsWith(skillsRoot + "/") && p[p.length - 1] === "MEMORY.md";
}

export function enabled(config: Config): boolean {
  return ((config.usage ?? {}) as { enabled?: unknown }).enabled !== false;
}

const line = (kind: string, id: string, op: string, at: string) =>
  JSON.stringify({ at, kind, id, op, surface: "connector", session: "connector" });

/** Record an open; never fails the read it accompanies. */
export async function recordOpen(store: UsageStore | undefined, repo: Repo, id: string, op: string, at: string, kind: "open" | "apply" = "open"): Promise<void> {
  if (!store) return;
  try {
    const config = await loadConfig(repo);
    if (!tracked(id, skillsRoot(config)) || !enabled(config)) return;
    const key = `${PREFIX}${at.replace(/[^0-9]/g, "")}-${Math.random().toString(36).slice(2, 10)}`;
    await store.put(key, line(kind, id, op, at), { expirationTtl: KEEP_S });
  } catch { /* usage never stands in the way of reading */ }
}

async function buffered(store: UsageStore): Promise<{ keys: string[]; lines: string[] }> {
  const keys: string[] = [];
  let cursor: string | undefined;
  do {
    const r = await store.list({ prefix: PREFIX, cursor });
    keys.push(...r.keys.map((k) => k.name));
    cursor = r.list_complete ? undefined : r.cursor;
  } while (cursor && keys.length < 1000);
  keys.sort();
  const lines: string[] = [];
  for (const k of keys) {
    const v = await store.get(k);
    if (v) lines.push(v);
  }
  return { keys, lines };
}

function pendingFile(lines: string[], now: string): Change {
  const stamp = now.replace(/[^0-9]/g, "").slice(0, 12);
  return { path: `${PENDING}/${stamp}-connector-${Math.random().toString(36).slice(2, 8)}.jsonl`, text: lines.join("\n") + "\n" };
}

/**
 * Commit the buffered opens, plus `extra` lines, as one pending file. Keys are deleted
 * only after the commit, so a failed commit loses nothing. Returns the number of lines.
 */
export async function flush(store: UsageStore | undefined, repo: Repo, now: string, by: string, extra: string[] = []): Promise<number> {
  const got = store ? await buffered(store) : { keys: [], lines: [] };
  const lines = [...got.lines, ...extra];
  if (!lines.length) return 0;
  const c = pendingFile(lines, now);
  const opens = lines.filter((l) => l.includes('"kind":"open"')).length;
  const msg = `USAGE: ${opens} opens, ${lines.length - opens} citations or cards applied\n\nAssisted-by: ${by}`;
  for (let attempt = 0; attempt < 2; attempt++) {
    const head = (await repo.head()).oid;
    if ((await repo.commit([c], msg, head)) === "ok") {
      if (store) for (const k of got.keys) await store.delete(k);
      return lines.length;
    }
  }
  throw new Refused("the vault kept changing underneath the usage write; try again");
}

/** `usage_cite`: record what an answer cited or which cards were applied, and flush. */
export async function cite(store: UsageStore | undefined, repo: Repo, a: { ids: unknown; kind?: string; op?: string }, now: string, by: string): Promise<string> {
  const kind = a.kind === "apply" ? "apply" : "cite";
  const raw = Array.isArray(a.ids) ? a.ids.map(String) : typeof a.ids === "string" ? [a.ids] : [];
  const ids = raw.map((s) => s.trim().replace(/^\/+/, "")).filter(Boolean);
  const sr = skillsRoot(await loadConfig(repo));
  const bad = ids.filter((i) => !tracked(i, sr));
  if (!ids.length) throw new Refused("ids must list the wiki notes cited or the cards applied, as paths");
  if (bad.length) throw new Refused(`not a wiki note or memory card path: ${bad.join(", ")}`);
  if (kind === "apply" && ids.some((i) => !i.startsWith("augment_memory/") && !i.endsWith("/MEMORY.md"))) throw new Refused("apply is for memory cards and skill memories; a wiki note is cited");
  if (!enabled(await loadConfig(repo))) return "usage recording is off in config.yaml; nothing recorded";
  const op = String(a.op ?? (kind === "apply" ? "recall" : "answer"));
  const n = await flush(store, repo, now, by, [...new Set(ids)].map((i) => line(kind, i, op, now)));
  return `recorded ${ids.length} ${kind === "apply" ? "applied card" : "citation"}${ids.length === 1 ? "" : "s"}; ${n} usage line${n === 1 ? "" : "s"} committed to ${PENDING}/, folded into the index by the nightly cycle`;
}
