import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import * as vault from "../src/vault";
import * as w from "../src/write";
import * as skillmem from "../src/skillmem";
import { serve } from "../src/mcp";
import { CONFIG, FakeKV, FakeRepo, INDEX } from "./fake";

const NOW = "2026-10-28 20:00";
const BY = "augment/connector";
const ROOT = "notes/ASSETS/skills";
const SCRIPTS = join(__dirname, "..", "..", "scripts");

function repo() {
  return new FakeRepo({ "augment_wiki/config.yaml": CONFIG, "augment_wiki/index.jsonl": INDEX,
    [`${ROOT}/drawing/SKILL.md`]: "---\nname: drawing\ndescription: d\n---\n# Drawing\n" });
}
const post = (body: unknown) => new Request("https://x/mcp", { method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json" } });
const call = async (ctx: any, name: string, args: object) =>
  (await (await serve(post({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name, arguments: args } }), ctx)).json() as any).result;

beforeEach(() => vault.clearCache());

describe("skill memory", () => {
  it("is empty at first, written by replacing the body, confirmed with seen, and found by memory_search", async () => {
    const r = repo(), kv = new FakeKV(), ctx = { repo: r, kv, now: () => NOW, by: BY };
    expect((await call(ctx, "skill_memory_get", { skill: "drawing" })).content[0].text).toMatch(/no memory yet/);
    expect((await call(ctx, "skill_memory_update", { skill: "drawing", body: "Elbow points are absolute.\nCentre sub-blocks numerically." })).isError).toBe(false);
    const text = r.files.get(`${ROOT}/drawing/MEMORY.md`)!.text;
    expect(text).toBe(`---\nskill: drawing\nupdated: ${NOW}\nseen: 1\nby: ${BY}\n---\nElbow points are absolute.\nCentre sub-blocks numerically.\n`);
    expect((await call(ctx, "skill_memory_update", { skill: "drawing", seen: true })).content[0].text).toContain("seen 2");
    expect((await call(ctx, "skill_memory_get", { skill: "drawing" })).content[0].text).toContain("Elbow points");
    expect((await call(ctx, "memory_search", { query: "elbow points" })).content[0].text).toContain(`${ROOT}/drawing/MEMORY.md  [skill]`);
    expect([...kv.data.values()].join("\n")).toContain(`"id":"${ROOT}/drawing/MEMORY.md"`);
  });

  it("refuses an unknown skill, a secret, an over-long body, and any other write path", async () => {
    const r = repo(), ctx = { repo: r, now: () => NOW, by: BY };
    expect((await call(ctx, "skill_memory_update", { skill: "nope", body: "x" })).content[0].text).toMatch(/no skill nope/);
    expect((await call(ctx, "skill_memory_update", { skill: "drawing", body: 'token = "ghp_abcdefghijklmnopqrstuvwxyz0123"' })).content[0].text).toMatch(/secret/);
    expect((await call(ctx, "skill_memory_update", { skill: "drawing", body: "a".repeat(3001) })).content[0].text).toMatch(/3000/);
    await expect(w.write(r, { path: `${ROOT}/drawing/MEMORY.md`, content: "x" }, NOW.slice(0, 10), BY)).rejects.toThrow(/skill_memory_update only/);
    await expect(w.edit(r, { path: `${ROOT}/drawing/MEMORY.md`, old: "x", new: "y" }, NOW.slice(0, 10), BY)).rejects.toThrow(/skill_memory_update only/);
  });

  const havePython = existsSync(join(SCRIPTS, "skill_memory.py")) && (() => { try { execFileSync("python3", ["-c", "import yaml"]); return true; } catch { return false; } })();
  it.runIf(havePython)("writes MEMORY.md byte for byte as skill_memory.py does", () => {
    const d = mkdtempSync(join(tmpdir(), "sm-"));
    mkdirSync(join(d, "augment_wiki"));
    writeFileSync(join(d, "augment_wiki/config.yaml"), CONFIG);
    mkdirSync(join(d, ROOT, "drawing"), { recursive: true });
    writeFileSync(join(d, ROOT, "drawing/SKILL.md"), "---\nname: drawing\n---\n");
    execFileSync("python3", [join(SCRIPTS, "skill_memory.py"), d, "set", "drawing", "--body", "One.\nTwo.", "--by", BY]);
    const py = readFileSync(join(d, ROOT, "drawing/MEMORY.md"), "utf-8");
    const stamp = /updated: (.*)/.exec(py)![1];
    expect(skillmem.render({ skill: "drawing", updated: stamp, seen: 1, by: BY }, "One.\nTwo.")).toBe(py);
  });
});
