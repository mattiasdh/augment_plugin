import { beforeEach, describe, expect, it } from "vitest";
import * as vault from "../src/vault";
import { serve } from "../src/mcp";
import { CONFIG, FakeKV, FakeRepo, INDEX, SEARCH } from "./fake";

const NOW = "2026-10-15 14:00";
const BY = "augment/connector";
const NOTE = "augment_wiki/concept/pace-layering.md";
const CARD = "augment_memory/card/some-card.md";

function setup(extraConfig = "") {
  const repo = new FakeRepo({
    "augment_wiki/config.yaml": CONFIG + extraConfig, "augment_wiki/index.jsonl": INDEX,
    [NOTE]: "---\ntype: concept\n---\n# Pace layering\n", "notes/40_LIBRARY/Pace layering.md": "---\naugment: \"#processed\"\n---\nSource.",
    [CARD]: "---\ntype: tool\ntitle: Some card\nsummary: s\nstatus: active\nscope: global\nseen: 1\n---\nBody.\n",
    "augment_memory/index.md": "# Memory\n",
  });
  const kv = new FakeKV();
  return { repo, kv, ctx: { repo, kv, now: () => NOW, by: BY } };
}
const post = (body: unknown) => new Request("https://x/mcp", { method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json" } });
const call = async (ctx: any, name: string, args: object) =>
  (await (await serve(post({ jsonrpc: "2.0", id: 1, method: "tools/call", params: { name, arguments: args } }), ctx)).json() as any).result;
const pending = (repo: FakeRepo) => [...repo.files.keys()].filter((p) => p.startsWith("augment_wiki/usage.pending/"));

beforeEach(() => vault.clearCache());

describe("usage", () => {
  it("buffers opens of wiki notes and cards, not of sources, without a commit", async () => {
    const { repo, kv, ctx } = setup();
    const before = repo.commits.length;
    await call(ctx, "vault_read", { path: NOTE });
    await call(ctx, "vault_read", { path: "notes/40_LIBRARY/Pace layering.md" });
    await call(ctx, "memory_get", { slug: "some-card" });
    expect(kv.data.size).toBe(2);
    expect(repo.commits.length).toBe(before);
    expect([...kv.data.values()].join("\n")).toContain(`"kind":"open","id":"${NOTE}"`);
  });

  it("commits citations with the buffered opens in one pending file, then clears the buffer", async () => {
    const { repo, kv, ctx } = setup();
    await call(ctx, "vault_read", { path: NOTE });
    const r = await call(ctx, "usage_cite", { ids: [NOTE], op: "answer" });
    expect(r.isError).toBe(false);
    expect(r.content[0].text).toContain("2 usage lines committed");
    const files = pending(repo);
    expect(files).toHaveLength(1);
    const lines = repo.files.get(files[0])!.text.trim().split("\n").map((l) => JSON.parse(l));
    expect(lines.map((l) => l.kind)).toEqual(["open", "cite"]);
    expect(kv.data.size).toBe(0);
    expect(repo.commits.at(-1)).toMatch(/^USAGE: 1 opens/);
  });

  it("refuses what is not a wiki note or card, and apply on a wiki note", async () => {
    const { ctx } = setup();
    expect((await call(ctx, "usage_cite", { ids: ["notes/40_LIBRARY/Pace layering.md"] })).content[0].text).toMatch(/^REFUSED: not a wiki note/);
    expect((await call(ctx, "usage_cite", { ids: [NOTE], kind: "apply" })).content[0].text).toMatch(/apply is for memory cards/);
    expect((await call(ctx, "usage_cite", { ids: [CARD], kind: "apply", op: "recall" })).isError).toBe(false);
  });

  it("flushes buffered opens at activate, and records nothing when usage is off", async () => {
    const { repo, ctx } = setup();
    await call(ctx, "vault_read", { path: NOTE });
    await call(ctx, "activate", {});
    expect(pending(repo)).toHaveLength(1);
    const off = setup("usage:\n  enabled: false\n");
    vault.clearCache();
    await call(off.ctx, "vault_read", { path: NOTE });
    expect(off.kv.data.size).toBe(0);
    expect((await call(off.ctx, "usage_cite", { ids: [NOTE] })).content[0].text).toMatch(/off/);
    expect(pending(off.repo)).toHaveLength(0);
  });

  it("marks when a search hit was last used, without reordering", async () => {
    const d = JSON.parse(SEARCH);
    d.notes[0].u = "2026-03-02";
    const repo = new FakeRepo({ "augment_wiki/config.yaml": CONFIG, "augment_wiki/index.jsonl": INDEX, "augment_wiki/search.json": JSON.stringify(d) });
    expect(await vault.search(repo, "pace layering")).toContain("(last used 2026-03-02)");
    vault.clearCache();
    expect(await vault.search(repo, "reuse channels")).toContain("(not used since usage recording began)");
  });
});
