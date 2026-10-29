import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import * as vault from "../src/vault";
import * as w from "../src/write";
import * as record from "../src/record";
import { serve } from "../src/mcp";
import { CONFIG, FakeRepo, INDEX } from "./fake";

const NOW = "2026-10-28 20:00";
const LATER = "2026-10-28 21:15";
const BY = "augment/connector";
const SCRIPTS = join(__dirname, "..", "..", "scripts");
const BODY = "## Goal\nDraft the Harbour energy memo.\n\n## State\nU-values checked.\n\n## Next steps\n- [ ] mdh: send to the engineer\n\n## Touched\n- notes/10_PROJECTS/301 Harbour/Memos/x.md\n\n## Resume\nOpen the memo and finish section 3.";

const repo = () => new FakeRepo({ "augment_wiki/config.yaml": CONFIG, "augment_wiki/index.jsonl": INDEX });
const post = (body: unknown) => new Request("https://x/mcp", { method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json" } });
const call = async (ctx: any, name: string, args: object) =>
  (await (await serve(post({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name, arguments: args } }), ctx)).json() as any).result;
const text = (r: any) => r.content[0].text as string;

beforeEach(() => vault.clearCache());

describe("session records", () => {
  it("mints an id, replaces the state on the next RECORD, finds it by words, and parks it", async () => {
    const r = repo();
    let t = NOW;
    const ctx = { repo: r, now: () => t, by: BY };
    const first = text(await call(ctx, "record_write", { title: "Harbour: energy memo", project: "301 Harbour", surface: "chat", body: BODY }));
    const id = /RECORD (R-\d{6}-[a-z2-7]{4}) created/.exec(first)![1];
    expect(id.startsWith("R-261028-")).toBe(true);
    t = LATER;
    expect(text(await call(ctx, "record_write", { id, body: BODY.replace("U-values checked.", "Memo sent.") }))).toContain(`version 2, superseding the state of ${NOW}`);
    const f = r.files.get(`augment_sessions/${id}.md`)!.text;
    expect(f).toContain("records: 2");
    expect(f).toContain(`created: ${NOW}`);
    expect(f).toContain("Memo sent.");
    expect(f).toContain('title: "Harbour: energy memo"');
    expect(r.commits.at(-1)).toMatch(new RegExp(`^RECORD: ${id} Harbour`));
    expect(text(await call(ctx, "record_search", { query: "harbour energy" }))).toContain(id);
    expect(text(await call(ctx, "record_search", { query: id }))).toMatch(/^100/);
    expect(text(await call(ctx, "record_write", { id, status: "parked" }))).toContain("now parked");
    expect(text(await call(ctx, "record_search", {}))).toContain("parked");
    expect(text(await call(ctx, "record_get", { id }))).toContain("## Resume");
    expect(text(await call(ctx, "activate", {}))).toContain("Session records not closed (1");
  });

  it("finds its own record again by session id, without the id", async () => {
    const r = repo(), ctx = { repo: r, now: () => NOW, by: BY };
    const id = /(R-\S+) created/.exec(text(await call(ctx, "record_write", { title: "T", session_id: "cse_9", body: BODY })))![1];
    expect(text(await call(ctx, "record_write", { session_id: "cse_9", body: BODY }))).toContain(`RECORD ${id} updated`);
    expect([...r.files.keys()].filter((k) => k.startsWith("augment_sessions/")).length).toBe(1);
  });

  it("keeps a pasted conversation address, derives a Code one, and refuses anything off claude.ai", async () => {
    const r = repo(), ctx = { repo: r, now: () => NOW, by: BY };
    const url = "https://claude.ai/chat/f6f8057e-68ff-438b-b2b9-4dd90672442b";
    const id = /(R-\S+) created/.exec(text(await call(ctx, "record_write", { title: "T", surface: "chat", session_url: url, body: BODY })))![1];
    await call(ctx, "record_write", { id, body: BODY });
    expect(r.files.get(`augment_sessions/${id}.md`)!.text).toContain(`session_url: ${url}`);
    const id2 = /(R-\S+) created/.exec(text(await call(ctx, "record_write", { title: "C", session_id: "cse_01Abc", body: BODY })))![1];
    expect(r.files.get(`augment_sessions/${id2}.md`)!.text).toContain("session_url: https://claude.ai/code/session_01Abc");
    expect(text(await call(ctx, "record_write", { title: "X", session_url: "https://example.com/x", body: BODY }))).toMatch(/claude.ai address/);
  });

  it("refuses a missing section, a secret, an unknown id, and vault_write into the folder", async () => {
    const r = repo(), ctx = { repo: r, now: () => NOW, by: BY };
    expect(text(await call(ctx, "record_write", { title: "T", body: "## Goal\nx" }))).toMatch(/missing section/);
    expect(text(await call(ctx, "record_write", { title: "T", body: BODY + '\ntoken = "ghp_abcdefghijklmnopqrstuvwxyz0123"' }))).toMatch(/secret/);
    expect(text(await call(ctx, "record_write", { id: "R-261028-aaaa", body: BODY }))).toMatch(/no record R-261028-aaaa/);
    expect(text(await call(ctx, "record_write", { title: "T", body: BODY.replace("## State", "## Statex") }))).toMatch(/missing section/);
    await expect(w.write(r, { path: "augment_sessions/R-261028-aaaa.md", content: "x" }, "2026-10-28", BY)).rejects.toThrow(/record_write only/);
  });

  const havePython = existsSync(join(SCRIPTS, "record_write.py")) && (() => { try { execFileSync("python3", ["-c", "import yaml"]); return true; } catch { return false; } })();
  it.runIf(havePython)("writes a record byte for byte as record_write.py does", () => {
    const d = mkdtempSync(join(tmpdir(), "rec-"));
    mkdirSync(join(d, "augment_wiki"));
    writeFileSync(join(d, "augment_wiki/config.yaml"), CONFIG);
    execFileSync("python3", [join(SCRIPTS, "record_write.py"), d, "write", "--title", "Harbour: energy memo", "--project", "301 Harbour",
      "--surface", "code", "--session-id", "cse_1", "--body", BODY, "--by", BY, "--now", NOW]);
    const name = readdirSync(join(d, "augment_sessions"))[0];
    const py = readFileSync(join(d, "augment_sessions", name), "utf-8");
    expect(record.render({ id: name.slice(0, -3), title: "Harbour: energy memo", status: "open", project: "301 Harbour", surface: "code",
      session_id: "cse_1", session_url: "https://claude.ai/code/session_1", created: NOW, updated: NOW, records: 1, by: BY }, BODY)).toBe(py);
    expect(record.checkBody(BODY)).toBeNull();
  });
});
