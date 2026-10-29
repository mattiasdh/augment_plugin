/**
 * Session records, `augment_sessions/<id>.md`: the connector's half of the plugin's
 * `scripts/record_write.py` (reference/sessions.md). The working state of one
 * conversation, replaced by every later RECORD of it, so a session on another surface
 * can resume the work. Chat is the surface that needs this most and the one that shows
 * Claude neither its conversation id nor its title, so the key is an id the first
 * RECORD mints. The folder is written through these tools only; vault_write refuses it.
 */
import type { Repo } from "./github";
import { Refused, q, secretIn, splitNote, tokens, type Front } from "./memory";

export const DIR = "augment_sessions";
const ORDER = ["id", "title", "status", "project", "surface", "session_id", "session_url", "created", "updated", "records", "by"];
const QUOTED = new Set(["title", "project"]);
export const STATUSES = ["open", "parked", "closed"] as const;
const SECTIONS = ["Goal", "State", "Next steps", "Touched", "Resume"];
export const BODY_MAX = 8000;
export const ID_RE = /^R-\d{6}-[a-z2-7]{4}$/;
const ALPHABET = "abcdefghijklmnopqrstuvwxyz234567";
const URL_RE = /^https:\/\/claude\.ai\/\S+$/;

/** The web address of a cloud Code session, from its `cse_` id; undefined for anything else. */
export function urlOf(sessionId: unknown): string | undefined {
  const m = /^cse_([A-Za-z0-9]+)$/.exec(String(sessionId ?? ""));
  return m ? `https://claude.ai/code/session_${m[1]}` : undefined;
}

export function render(fm: Front, body: string): string {
  const lines = ["---"];
  for (const k of ORDER) {
    const v = fm[k];
    if (v === undefined || v === null || v === "") continue;
    lines.push(QUOTED.has(k) ? `${k}: ${q(v)}` : `${k}: ${v}`);
  }
  lines.push("---");
  return lines.join("\n") + "\n" + body.replace(/^\n+|\n+$/g, "") + "\n";
}

/** Why a body is refused, or null; the same tests as record_write.py's check_body. */
export function checkBody(body: string): string | null {
  const b = (body ?? "").trim();
  if (!b) return "a record needs its body (the five sections)";
  if (b.length > BODY_MAX) return `${b.length} characters; ${BODY_MAX} at most. A record is the working state, not a transcript: decisions and findings belong in the notes (capture_note), and the record links them`;
  const heads = [...b.matchAll(/^## +(.+?)\s*$/gm)].map((m) => m[1].trim());
  const found = heads.filter((h) => SECTIONS.includes(h));
  const missing = SECTIONS.filter((s) => !found.includes(s));
  if (missing.length) return "missing section(s): " + missing.map((s) => `## ${s}`).join(", ");
  if (found.join("|") !== SECTIONS.join("|")) return "sections out of order; they run " + SECTIONS.join(" / ");
  const hit = secretIn(b);
  if (hit) return `that looks like a secret (${hit}); a record never holds one`;
  return null;
}

const pathOf = (id: string) => `${DIR}/${id}.md`;

interface Rec { id: string; fm: Front; body: string }

async function load(repo: Repo): Promise<Rec[]> {
  const files = await repo.readDir(DIR).catch(() => []);
  const out: Rec[] = [];
  for (const f of files) {
    const name = f.path.split("/").pop()!;
    if (!name.endsWith(".md") || !ID_RE.test(name.slice(0, -3))) continue;
    const [fm, body] = splitNote(f.text);
    out.push({ id: name.slice(0, -3), fm, body });
  }
  return out.sort((a, b) => (String(a.fm.updated ?? "") < String(b.fm.updated ?? "") ? 1 : -1));
}

const line = (r: Rec) =>
  `${r.id}  ${String(r.fm.status ?? "?").padEnd(6)}  ${r.fm.updated ?? "?"}${r.fm.project ? `  [${r.fm.project}]` : ""}  ${r.fm.title ?? ""}`;

async function mint(repo: Repo, now: string): Promise<string> {
  const d = now.slice(2, 10).replace(/-/g, "");
  for (let i = 0; i < 50; i++) {
    let id = `R-${d}-`;
    for (let j = 0; j < 4; j++) id += ALPHABET[Math.floor(Math.random() * ALPHABET.length)];
    if (!(await repo.read(pathOf(id)))) return id;
  }
  throw new Refused("could not mint a free id");
}

export interface WriteArgs { id?: string; title?: string; status?: string; project?: string; surface?: string; session_id?: string; session_url?: string; body?: string }

export async function write(repo: Repo, a: WriteArgs, now: string, by: string): Promise<string> {
  if (a.status && !(STATUSES as readonly string[]).includes(a.status)) throw new Refused(`status is one of ${STATUSES.join(", ")}`);
  if (a.session_url && !URL_RE.test(a.session_url)) throw new Refused("session_url is the conversation's claude.ai address (https://claude.ai/...)");
  if (a.id && !ID_RE.test(a.id)) throw new Refused(`${a.id} is not a record id (R-YYMMDD-xxxx)`);
  const statusOnly = a.body === undefined;
  if (statusOnly) {
    if (!a.id || !a.status) throw new Refused("give body (the five sections) to record the state, or id and status alone to open, park or close a record");
  } else {
    const why = checkBody(a.body!);
    if (why) throw new Refused(why);
  }
  for (let attempt = 0; attempt < 2; attempt++) {
    const head = (await repo.head()).oid;
    let id = a.id ?? "";
    if (!id && a.session_id) id = (await load(repo)).find((r) => String(r.fm.session_id ?? "") === a.session_id)?.id ?? "";
    const cur = id ? await repo.read(pathOf(id)) : null;
    if (a.id && !cur) throw new Refused(`no record ${a.id}; omit id to start a new one, or record_search for the right id`);
    const [cfm, cbody] = cur ? splitNote(cur.text) : [{} as Front, ""];
    let text: string, msg: string, done: string;
    if (statusOnly) {
      text = render({ ...cfm, status: a.status, updated: now, by }, cbody);
      msg = `RECORD: ${id} ${a.status}`;
      done = `RECORD ${id} is now ${a.status}.`;
    } else {
      const title = a.title ?? (cfm.title as string | undefined);
      if (!title) throw new Refused("a new record needs a title");
      const isNew = !cur;
      if (isNew) id = await mint(repo, now);
      const fm: Front = {
        id, title, status: a.status ?? cfm.status ?? "open", project: a.project ?? cfm.project, surface: a.surface ?? cfm.surface,
        session_id: a.session_id ?? cfm.session_id,
        session_url: a.session_url ?? urlOf(a.session_id) ?? cfm.session_url ?? urlOf(cfm.session_id), created: cfm.created ?? now, updated: now,
        records: isNew ? 1 : Number(cfm.records ?? 0) + 1, by,
      };
      text = render(fm, a.body!);
      msg = `RECORD: ${id} ${title}`;
      done = isNew ? `RECORD ${id} created (${pathOf(id)}). Quote this id to resume or update it from any surface.`
        : `RECORD ${id} updated, version ${fm.records}, superseding the state of ${cfm.updated ?? "?"} (${pathOf(id)}).`;
    }
    if ((await repo.commit([{ path: pathOf(id), text }], `${msg}\n\nAssisted-by: ${by}`, head)) === "ok") return done;
  }
  throw new Refused("the vault kept changing underneath this write; read again and retry");
}

export async function get(repo: Repo, id: string): Promise<string> {
  const f = ID_RE.test(id) ? await repo.read(pathOf(id)) : null;
  if (!f) throw new Refused(`no record ${id}; record_search for it`);
  return f.text;
}

/** Records matching the words (id or session id exactly, else title and project 3, body 1); no words lists the live ones. */
export async function search(repo: Repo, query: string, status = "all"): Promise<string> {
  const recs = (await load(repo)).filter((r) => status === "all" || (status === "live" ? r.fm.status !== "closed" : r.fm.status === status));
  const words = String(query ?? "").trim().split(/\s+/).filter(Boolean);
  if (!words.length) return recs.map(line).join("\n") || "no records";
  const qt = tokens(words.join(" "));
  const hits: [number, string, Rec][] = [];
  for (const r of recs) {
    if (words.some((w) => w === r.id || w === String(r.fm.session_id ?? ""))) { hits.push([100, String(r.fm.updated ?? ""), r]); continue; }
    const head = tokens(`${r.fm.title ?? ""} ${r.fm.project ?? ""}`), rest = tokens(r.body);
    let s = 0;
    for (const t of qt) s += 3 * +head.has(t) + +rest.has(t);
    if (s) hits.push([s, String(r.fm.updated ?? ""), r]);
  }
  hits.sort((x, y) => (y[0] - x[0]) || (x[1] < y[1] ? 1 : x[1] > y[1] ? -1 : 0));
  return hits.map(([s, , r]) => `${String(s).padStart(3)}  ${line(r)}`).join("\n") || "no record matches";
}

/** One line per live record, newest first, for activate. */
export async function live(repo: Repo, max = 8): Promise<string> {
  const recs = (await load(repo)).filter((r) => r.fm.status !== "closed");
  if (!recs.length) return "";
  const shown = recs.slice(0, max).map((r) => "- " + line(r));
  return `Session records not closed (${recs.length}; resume one with record_get):\n${shown.join("\n")}${recs.length > max ? `\n- … ${recs.length - max} more (record_search)` : ""}\n`;
}
