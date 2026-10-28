/**
 * A skill's own memory, `<skills root>/<skill>/MEMORY.md`: the connector's half of the
 * plugin's `scripts/skill_memory.py` (reference/skills.md). The current lessons of one
 * skill, read at its Preflight and rewritten at the end of a run, from any surface,
 * with the same cap and secret refusal as a memory card. The file is written through
 * these tools only; vault_write and vault_edit refuse it.
 */
import type { Repo } from "./github";
import { BODY_MAX, Refused, secretIn, seenOf, splitNote, tokens } from "./memory";
import { loadConfig, skillsRoot } from "./vault";
import * as usage from "./usage";

const ORDER = ["skill", "updated", "seen", "by"];

export function render(fm: Record<string, unknown>, body: string): string {
  const lines = ["---", ...ORDER.filter((k) => fm[k] !== undefined && fm[k] !== "").map((k) => `${k}: ${fm[k]}`), "---"];
  return lines.join("\n") + "\n" + body.replace(/^\n+|\n+$/g, "") + "\n";
}

async function where(repo: Repo, skill: string): Promise<string> {
  const root = skillsRoot(await loadConfig(repo));
  if (!root) throw new Refused("config.yaml declares no skills root (skills: root:)");
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(skill)) throw new Refused(`${skill} is not a skill folder name`);
  if (!(await repo.read(`${root}/${skill}/SKILL.md`))) throw new Refused(`no skill ${skill} under ${root}/ (no SKILL.md)`);
  return `${root}/${skill}/MEMORY.md`;
}

export async function get(repo: Repo, skill: string, ctx: { kv?: usage.UsageStore; now: string }): Promise<string> {
  const path = await where(repo, skill);
  const f = await repo.read(path);
  if (!f || !splitNote(f.text)[1].trim()) return `${skill}: no memory yet (${path}). Work from the skill's references, and write what this run learns with skill_memory_update.`;
  await usage.recordOpen(ctx.kv, repo, path, "skill_memory_get", ctx.now);
  return f.text;
}

export async function update(repo: Repo, a: { skill: string; body?: string; seen?: boolean }, now: string, by: string, kv?: usage.UsageStore): Promise<string> {
  const path = await where(repo, a.skill);
  const body = a.body === undefined ? undefined : String(a.body);
  if (body !== undefined) {
    if (!body.trim()) throw new Refused("body must hold the current lessons; to keep them, pass seen alone");
    if (body.trim().length > BODY_MAX) throw new Refused(`${body.trim().length} characters; ${BODY_MAX} at most. Promote settled lessons into the skill's references/ (with the person's approval) and keep MEMORY.md to what is recent.`);
    const hit = secretIn(body);
    if (hit) throw new Refused(`that looks like a secret (${hit}); memory never holds one`);
  } else if (!a.seen) throw new Refused("give body (the lessons, replacing what is there), seen, or both");
  for (let attempt = 0; attempt < 2; attempt++) {
    const head = (await repo.head()).oid;
    const cur = await repo.read(path);
    const [fm, old] = cur ? splitNote(cur.text) : [{}, ""];
    if (body === undefined && !old.trim()) throw new Refused(`${a.skill} has no memory to confirm`);
    const seen = seenOf(fm) + (a.seen ? 1 : 0);
    const text = render({ skill: a.skill, updated: now, seen: cur ? seen : 1, by }, body ?? old);
    const msg = `MEMORY: ${body !== undefined ? "update" : "seen"} skill ${a.skill}\n\nAssisted-by: ${by}`;
    if ((await repo.commit([{ path, text }], msg, head)) === "ok") {
      await usage.recordOpen(kv, repo, path, "skill_memory_update", now, "apply");
      return `${body !== undefined ? "wrote" : "confirmed"} ${path}${a.seen ? ` (seen ${seen})` : ""}`;
    }
  }
  throw new Refused("the vault kept changing underneath this write; read again and retry");
}

/** Skill memories matching a query, scored as `memory_search.py` scores them (name 3, first line 2, body 1). */
export async function search(repo: Repo, query: string): Promise<string[]> {
  const root = skillsRoot(await loadConfig(repo));
  if (!root) return [];
  const qt = tokens(query);
  const dirs = ((await repo.list(root)) ?? []).filter((e) => e.type === "dir" && !e.name.startsWith(".") && !e.name.startsWith("_"));
  const hits: [number, string][] = [];
  for (const d of dirs) {
    const f = await repo.read(`${root}/${d.name}/MEMORY.md`);
    if (!f) continue;
    const body = splitNote(f.text)[1];
    const first = body.split("\n").map((l) => l.trim()).find(Boolean) ?? "";
    const name = tokens(d.name), summary = tokens(first.slice(0, 160)), rest = tokens(body);
    let s = 0;
    for (const t of qt) s += 3 * +name.has(t) + 2 * +summary.has(t) + +rest.has(t);
    if (s) hits.push([s, `${String(s).padStart(3)}  ${root}/${d.name}/MEMORY.md  [skill]  ${first.slice(0, 160)}`]);
  }
  return hits.sort((a, b) => b[0] - a[0]).map(([, l]) => l);
}
