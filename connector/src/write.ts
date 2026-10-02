/**
 * The connector's column of the plugin's `rules/surfaces.md` table: the same file
 * primitives Tier 2 has through Obsidian and `augment-runner`, under the same
 * Never list, checked here in code.
 *
 *   vault_list      what a folder holds, as far as the reading rules open it
 *   vault_write     a new note anywhere a note may be created; a whole wiki note or
 *                   skill file replaced; never an existing source
 *   vault_edit      one exact passage of a skill file replaced, with its CHANGELOG line
 *   source_set      a source's system key, as `source_write.py set`
 *   source_callout  a comment on a source, as `source_write.py callout`
 *   append_history  ledger entries, parked in augment_wiki/history.pending/ because
 *                   GitHub cannot append to a file; `compact_index.py` merges them
 *
 * Never: replace or edit an existing source, write into augment_memory/ (the
 * memory tools do), write index.jsonl or history.jsonl, delete or move anything,
 * or reach a folder config.yaml ignores, rules out or has not ruled on.
 * Every write is one commit made against the head it read, so it never lands on
 * top of a change it did not see.
 */
import type { Change, Repo } from "./github";
import { Refused, splitNote } from "./memory";
import { cleanPath, loadConfig, scopeOf, skillsRoot, type Config } from "./vault";
import { contentHash, KEYS, SourceRefused, writeCallout, writeKey } from "./source";

type Place = "wiki" | "memory" | "skill" | "inbox" | "source" | "closed";

const CLOSED: Record<string, string> = {
  ignore: "is in a folder the vault's config.yaml ignores",
  out: "is in a folder the vault's config.yaml rules out of scope",
  undecided: "is in a folder the vault's config.yaml has not ruled on yet, and an unruled folder stays closed",
};

function inbox(config: Config): string {
  const root = String(config.source_root ?? "").replace(/^\/+|\/+$/g, "");
  return root ? `${root}/_inbox` : "_inbox";
}

/** Where a path sits, for the write rules, and why it is closed when it is. */
export function place(path: string, config: Config): [Place, string] {
  if (path.startsWith("augment_memory/")) return ["memory", ""];
  if (path.startsWith("augment_wiki/")) return ["wiki", ""];
  const sr = skillsRoot(config);
  if (sr && path.startsWith(sr + "/")) return ["skill", ""];
  if (path.startsWith(inbox(config) + "/")) return ["inbox", ""];
  const s = scopeOf(path, config);
  return s === "in" ? ["source", ""] : ["closed", CLOSED[s]];
}

function mdPath(path: string): string {
  const p = cleanPath(path);
  if (!p.endsWith(".md")) throw new Refused("only markdown notes are written through the connector; index.jsonl and history.jsonl never are");
  return p;
}

/** One commit against the head read first; a moved head is retried once, from a fresh read. */
async function commitFresh(repo: Repo, message: string, build: () => Promise<Change[]>): Promise<void> {
  for (let attempt = 0; attempt < 2; attempt++) {
    const head = (await repo.head()).oid;
    const changes = await build();
    if (!changes.length) return;
    if ((await repo.commit(changes, message, head)) === "ok") return;
  }
  throw new Refused("the vault kept changing underneath this write; read again and retry");
}

// ---- vault_list ----

export async function list(repo: Repo, folder: string): Promise<string> {
  const dir = String(folder ?? "").trim().replace(/^\/+|\/+$/g, "");
  if (dir) cleanPath(dir);
  const config = await loadConfig(repo);
  const entries = await repo.list(dir);
  if (!entries) throw new Refused(`no folder ${dir || "(root)"}`);
  const lines: string[] = [];
  for (const e of entries) {
    if (e.name.startsWith(".")) continue;
    const [where] = place(e.type === "dir" ? e.path + "/x.md" : e.path, config);
    if (where === "closed") {
      const sc = scopeOf(e.path + "/x.md", config);
      if (e.type === "dir" && sc !== "ignore") lines.push(`${e.path}/  (closed: ${sc === "out" ? "ruled out of scope" : "not ruled on yet"})`);
      continue;
    }
    lines.push(e.type === "dir" ? `${e.path}/` : e.path);
  }
  return lines.length ? lines.join("\n") : `${dir || "(root)"} holds nothing the connector may open`;
}

// ---- vault_write ----

function changelogChange(skillDir: string, line: string, today: string, existing: string | null, ref: string): Change {
  const entry = `- ${today}: ${line.replace(/\s*\n\s*/g, " ").trim()} (${ref})`;
  const base = existing ?? `# ${skillDir.split("/").pop()} changelog\n\nOne dated line per approved rule change, newest first.\n`;
  const lines = base.replace(/\n+$/, "").split("\n");
  const first = lines.findIndex((l) => l.startsWith("- "));
  if (first >= 0) lines.splice(first, 0, entry);
  else lines.push("", entry);
  return { path: `${skillDir}/CHANGELOG.md`, text: lines.join("\n") + "\n" };
}

/** The skill folder and the reference file's name when `path` is a skill's reference, else null. */
function referenceOf(path: string, config: Config): [string, string] | null {
  const sr = skillsRoot(config);
  if (!sr || !path.startsWith(sr + "/")) return null;
  const rest = path.slice(sr.length + 1).split("/");
  return rest.length >= 3 && rest[1] === "references" ? [`${sr}/${rest[0]}`, rest.slice(1).join("/")] : null;
}

export async function write(repo: Repo, a: { path: string; content: string; changelog?: string }, today: string, by: string): Promise<string> {
  const p = mdPath(a.path);
  const text = String(a.content ?? "");
  if (!text.trim()) throw new Refused("a note needs content");
  const config = await loadConfig(repo);
  const [where, why] = place(p, config);
  if (where === "memory") throw new Refused("augment_memory/ is written through the memory tools only (memory_add, memory_update, ...)");
  if (where === "closed") throw new Refused(`${p} ${why}`);
  const ref = referenceOf(p, config);
  if (ref && !a.changelog?.trim()) throw new Refused(`${p} is a skill's reference: an approved rule change carries its CHANGELOG line (changelog)`);
  let verb = "";
  await commitFresh(repo, `WRITE: ${p}\n\nAssisted-by: ${by}`, async () => {
    const cur = await repo.read(p);
    if (cur && (where === "source" || where === "inbox"))
      throw new Refused(`${p} exists: sources are append-only. A comment goes through source_callout, a status through source_set, and anything else is the person's own edit`);
    if (!cur && (where === "source" || where === "inbox") && !splitNote(text)[0].augment)
      throw new Refused("a new source note carries its declaration in frontmatter (augment: \"#to-process\", created:, updated:, and assisted_by: when Claude drafted any of it)");
    if (cur && cur.text === text) return [];
    verb = cur ? "replaced" : "created";
    const out: Change[] = [{ path: p, text }];
    if (ref) out.push(changelogChange(ref[0], a.changelog!, today, (await repo.read(`${ref[0]}/CHANGELOG.md`))?.text ?? null, ref[1]));
    return out;
  });
  if (!verb) return `${p} already holds exactly this; nothing written`;
  const after = where === "wiki" ? " A wiki note is compiled output: its ledger entry and index line come from the operation that wrote it (process or mint), which needs a script-capable surface." :
    where === "skill" ? " The skill's upload package in dist/ is rebuilt by the nightly cycle (package_skill.py)." : "";
  return `${verb} ${p}${ref ? ", with its CHANGELOG line" : ""}.${after}`;
}

// ---- vault_edit ----

export async function edit(repo: Repo, a: { path: string; old: string; new: string; changelog?: string }, today: string, by: string): Promise<string> {
  const p = mdPath(a.path);
  const config = await loadConfig(repo);
  const [where, why] = place(p, config);
  if (where !== "skill") {
    throw new Refused(where === "source" || where === "inbox" ? `${p} is a source, and sources are append-only: comment with source_callout` :
      where === "wiki" ? `${p} is a wiki note: hand edits are overwritten by the next build; correct it through its sources (write, correction mode)` :
      where === "memory" ? "augment_memory/ is written through the memory tools only" : `${p} ${why}`);
  }
  const old = String(a.old ?? "");
  if (!old) throw new Refused("old must be the exact passage to replace");
  const ref = referenceOf(p, config);
  if (ref && !a.changelog?.trim()) throw new Refused(`${p} is a skill's reference: an approved rule change carries its CHANGELOG line (changelog)`);
  await commitFresh(repo, `SKILL: ${p}\n\nAssisted-by: ${by}`, async () => {
    const cur = await repo.read(p);
    if (!cur) throw new Refused(`no file at ${p}`);
    const n = cur.text.split(old).length - 1;
    if (n !== 1) throw new Refused(n ? `the passage occurs ${n} times in ${p}; quote enough to make it unique` : `the passage is not in ${p}; read it again, it may have changed`);
    const out: Change[] = [{ path: p, text: cur.text.replace(old, () => String(a.new ?? "")) }];
    if (ref) out.push(changelogChange(ref[0], a.changelog!, today, (await repo.read(`${ref[0]}/CHANGELOG.md`))?.text ?? null, ref[1]));
    return out;
  });
  return `edited ${p}${ref ? ", with its CHANGELOG line" : ""}. The upload package in dist/ is rebuilt by the nightly cycle; tell the person to upload it afterwards.`;
}

// ---- source_set, source_callout ----

async function sourceFor(repo: Repo, path: string): Promise<string> {
  const p = mdPath(path);
  const [where, why] = place(p, await loadConfig(repo));
  if (where === "closed") throw new Refused(`${p} ${why}`);
  if (where !== "source" && where !== "inbox") throw new Refused(`${p} is not a source note`);
  return p;
}

const VALUE: Record<string, RegExp> = {
  augment: /^#[a-z][a-z-]*$/,
  created: /^\d{4}-\d{2}-\d{2}( \d{2}:\d{2})?$/,
  updated: /^\d{4}-\d{2}-\d{2}( \d{2}:\d{2})?$/,
  assisted_by: /^[a-z0-9-]+\/[A-Za-z0-9._-]+$/,
};

export async function sourceSet(repo: Repo, a: { path: string; key: string; value: string }, by: string): Promise<string> {
  const p = await sourceFor(repo, a.path);
  const key = String(a.key ?? "");
  if (!(KEYS as readonly string[]).includes(key)) throw new Refused(`${key} is not a system key; only ${KEYS.join(", ")} are written`);
  const v = String(a.value ?? "").trim();
  if (!VALUE[key].test(v)) throw new Refused(`${v} is not a valid ${key} value`);
  let changed = false;
  await commitFresh(repo, `SOURCE: ${key} ${v} on ${p}\n\nAssisted-by: ${by}`, async () => {
    const cur = await repo.readExact(p);
    if (!cur) throw new Refused(`no note at ${p}`);
    let out: string | null;
    try { out = await writeKey(cur.text, key, v); } catch (e) { throw e instanceof SourceRefused ? new Refused(`${p}: ${e.message}`) : e; }
    changed = out !== null;
    return out === null ? [] : [{ path: p, text: out }];
  });
  return changed ? `set ${key} on ${p}` : `${p} already has ${key}: ${v}`;
}

export async function sourceCallout(repo: Repo, a: { path: string; text: string; kind?: string; heading?: string }, now: string, by: string): Promise<string> {
  const p = await sourceFor(repo, a.path);
  const kind = a.kind === "note" ? "note" : "ai";
  const config = await loadConfig(repo);
  const actor = kind === "ai" ? by : String(config.author ?? "").trim();
  if (!actor) throw new Refused("a [!note] callout carries the person's name from `author:` in augment_wiki/config.yaml, and none is set; ask for it, and add it where a script-capable surface can, or write it as [!ai] only if Claude composed it");
  const text = String(a.text ?? "").trim();
  if (!text) throw new Refused("a callout needs its text");
  let hashes: [string, string] = ["", ""];
  await commitFresh(repo, `COMMENT: ${p}\n\n${kind === "ai" ? `Assisted-by: ${by}` : ""}`.trim(), async () => {
    const cur = await repo.readExact(p);
    if (!cur) throw new Refused(`no note at ${p}`);
    if (String(splitNote(cur.text)[0].augment ?? "").includes("#excluded")) throw new Refused(`${p} is declared #excluded`);
    let out: string;
    try { out = writeCallout(cur.text, kind, actor, now.slice(0, 10), text, now, a.heading); }
    catch (e) { throw e instanceof SourceRefused ? new Refused(`${p}: ${e.message}`) : e; }
    hashes = [await contentHash(cur.text), await contentHash(out)];
    const entry = { id: `comment-run-${now.slice(0, 10)}-${p.split("/").pop()!.replace(/\.md$/, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60)}`,
      kind: "comment_run", ran: now.slice(0, 10), source: p, old_hash: hashes[0], new_hash: hashes[1], by,
      restaled: [], note: "Written through the connector; the wiki notes compiled from this source are re-staled by the next detect_changes run." };
    return [{ path: p, text: out }, pending([entry], now)];
  });
  return `commented on ${p} (hash ${hashes[0]} -> ${hashes[1]}). The wiki notes compiled from it go stale at the next nightly detect, and are rebuilt from the source with the comment.`;
}

// ---- append_history ----

export const PENDING = "augment_wiki/history.pending";

function pending(entries: object[], now: string): Change {
  const stamp = now.replace(/[^0-9]/g, "").slice(0, 12);
  const rand = Math.random().toString(36).slice(2, 8);
  return { path: `${PENDING}/${stamp}-${rand}.jsonl`, text: entries.map((e) => JSON.stringify(e)).join("\n") + "\n" };
}

export async function appendHistory(repo: Repo, entries: unknown, now: string, by: string): Promise<string> {
  if (!Array.isArray(entries) || !entries.length) throw new Refused("entries must be a non-empty list of objects");
  entries.forEach((e, i) => {
    if (!e || typeof e !== "object" || Array.isArray(e) || typeof (e as { id?: unknown }).id !== "string" || !(e as { id: string }).id)
      throw new Refused(`entry ${i} is not an object with a string id; nothing written`);
  });
  const c = pending(entries as object[], now);
  await commitFresh(repo, `LEDGER: ${entries.length} pending entr${entries.length === 1 ? "y" : "ies"}\n\nAssisted-by: ${by}`, async () => [c]);
  return `parked ${entries.length} entr${entries.length === 1 ? "y" : "ies"} in ${c.path}; compact_index.py merges them into history.jsonl at the next script-capable run (the nightly cycle at the latest)`;
}
