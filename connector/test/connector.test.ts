import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import { Memory, render, slugify, tokens, jaccard, cardTokens, settingsFrom } from "../src/memory";
import { serve, TOOLS } from "../src/mcp";
import * as vault from "../src/vault";
import { CONFIG, FakeRepo, INDEX } from "./fake";

const NOW = "2026-09-27 14:02";
const BY = "augment/connector";
const SCRIPTS = join(__dirname, "..", "..", "scripts");

function python(code: string): string | null {
  try {
    return execFileSync("python3", ["-c", code], { cwd: SCRIPTS, encoding: "utf-8" });
  } catch {
    return null;
  }
}
const havePython = existsSync(join(SCRIPTS, "_memory.py")) && python("import yaml") !== null;

function vaultRepo(extra: Record<string, string> = {}) {
  return new FakeRepo({ "augment_wiki/config.yaml": CONFIG, "augment_wiki/index.jsonl": INDEX, ...extra });
}

beforeEach(() => vault.clearCache());

describe.runIf(havePython)("parity with the plugin's Python", () => {
  const cases = [
    "Obsidian REST patch rewrites the whole file",
    "Déliverable naming: YYMMDD_project_subject.pdf (always)",
    "git push --force-with-lease, never plain --force",
    "Reuse the pdf2md skill's links/ folder",
  ];

  it("tokenises, slugifies and scores as _memory.py does", () => {
    const out = python(`import json, _memory as M
cases = ${JSON.stringify(cases)}
print(json.dumps({"tokens": [sorted(M.tokens(c)) for c in cases], "slugs": [M.slugify(c) for c in cases],
  "jac": M.jaccard(M.tokens(cases[0]), M.tokens(cases[1] + " " + cases[0]))}))`);
    const py = JSON.parse(out!);
    expect(cases.map((c) => [...tokens(c)].sort())).toEqual(py.tokens);
    expect(cases.map(slugify)).toEqual(py.slugs);
    expect(jaccard(tokens(cases[0]), tokens(cases[1] + " " + cases[0]))).toBeCloseTo(py.jac, 10);
  });

  it("renders a card byte for byte as memory_write.py does", () => {
    const fm = { type: "preference", title: 'Naming "deliverables"', summary: "Date first: YYMMDD_project_subject.pdf; é ok.",
      status: "active", scope: ["memos", "bim-template"], keywords: ["naming", "pdf"], seen: 2, created: NOW, updated: NOW, by: BY };
    const body = "\n\nThe body.\n\n```bash\necho hi\n```\n\n";
    const out = python(`import json, _memory as M
print(M.render(json.loads(${JSON.stringify(JSON.stringify(fm))}), ${JSON.stringify(body)}), end="")`);
    expect(render(fm, body)).toBe(out);
    const single = { ...fm, scope: ["global"], keywords: [] };
    const out2 = python(`import json, _memory as M
print(M.render(json.loads(${JSON.stringify(JSON.stringify(single))}), ""), end="")`);
    expect(render(single, "")).toBe(out2);
  });

  it("decides scope as _gen_util.scope_of does", () => {
    const paths = ["notes/40_LIBRARY/a.md", "notes/40_LIBRARY/private/b.md", "notes/_inbox/c.md", "notes/PERSONAL/d.md",
      "notes/PERSONAL/READING/e.md", "notes/OTHER/f.md", "notes/40_LIBRARYX/g.md"];
    const out = python(`import json, yaml, _gen_util as G
cfg = yaml.safe_load(${JSON.stringify(CONFIG)})
print(json.dumps([G.scope_of(p, cfg) for p in ${JSON.stringify(paths)}]))`);
    const cfg = { scope: { ignore: ["notes/_inbox"], rules: [
      { path: "notes/40_LIBRARY", in_scope: true }, { path: "notes/40_LIBRARY/private", in_scope: false },
      { path: "notes/PERSONAL", in_scope: false }, { path: "notes/PERSONAL/READING", in_scope: true }] } };
    expect(paths.map((p) => vault.scopeOf(p, cfg))).toEqual(JSON.parse(out!));
  });
});

describe("memory", () => {
  let repo: FakeRepo;
  let m: Memory;
  beforeEach(() => {
    repo = vaultRepo();
    m = new Memory(repo, settingsFrom({}), () => NOW, BY);
  });

  it("adds a card, then refuses a near-duplicate and names it", async () => {
    await m.add({ type: "tool", title: "Obsidian REST patch rewrites the whole file", summary: "vault_patch rewrites the file; use source_write.py for sources.", keywords: "obsidian,rest" });
    expect(repo.files.has("augment_memory/card/obsidian-rest-patch-rewrites-the-whole-file.md")).toBe(true);
    await expect(m.add({ type: "tool", title: "Obsidian REST patch rewrites whole file", summary: "vault_patch rewrites the file", keywords: ["obsidian", "rest"] }))
      .rejects.toThrow(/LIKELY SAME as active card obsidian-rest-patch-rewrites-the-whole-file/);
    expect(repo.commits[0]).toMatch(/^MEMORY: add obsidian-rest-patch-rewrites-the-whole-file\n\nAssisted-by: augment\/connector/);
  });

  it("refuses secrets, long titles and bad types", async () => {
    await expect(m.add({ type: "snippet", title: "Push", summary: "x", body: 'token = "ghp_abcdefghijklmnopqrstuvwxyz0123"' })).rejects.toThrow(/secret/);
    await expect(m.add({ type: "tool", title: "one two three four five six seven eight nine ten eleven", summary: "x" })).rejects.toThrow(/ten at most/);
    await expect(m.add({ type: "fact", title: "x", summary: "x" })).rejects.toThrow(/type must be/);
    await expect(m.add({ type: "tool", title: "x", summary: "a".repeat(161) })).rejects.toThrow(/160/);
  });

  it("confirms, updates and supersedes by compare-and-swap", async () => {
    await m.add({ type: "preference", title: "Deliverable file naming", summary: "YYMMDD_project_subject.pdf" });
    expect(await m.seen("deliverable-file-naming")).toBe("deliverable-file-naming: seen 2");
    await m.update("deliverable-file-naming", { summary: "Date first: YYMMDD_project_subject.pdf", scope: "memos" });
    const text = (await repo.read("augment_memory/card/deliverable-file-naming.md"))!.text;
    expect(text).toContain('summary: "Date first: YYMMDD_project_subject.pdf"');
    expect(text).toContain("scope: memos");
    expect(text).toContain("seen: 2");
    await m.add({ type: "preference", title: "Folder naming for exports", summary: "Exports go in a dated folder" });
    await m.supersede("deliverable-file-naming", "folder-naming-for-exports");
    expect((await repo.read("augment_memory/card/deliverable-file-naming.md"))!.text).toContain("status: superseded\nsuperseded_by: folder-naming-for-exports");
    await expect(m.seen("../../notes/x")).rejects.toThrow(/not a card slug/);
  });

  it("loads project cards first, then global, and searches", async () => {
    await m.add({ type: "tool", title: "Archicad export quirk", summary: "IFC export drops zone names", scope: "bim-template" });
    await m.add({ type: "preference", title: "British spelling", summary: "EN-UK spelling in English deliverables" });
    await m.add({ type: "tool", title: "Unrelated project tool", summary: "only for another repo", scope: "other" });
    const ctx = await m.context("bim-template");
    const lines = ctx.split("\n");
    expect(lines[0]).toMatch(/2 cards for this session \(1 scoped to bim-template, 1 global\)/);
    expect(lines[1]).toContain("[[archicad-export-quirk]]");
    expect(ctx).not.toContain("unrelated");
    expect(await m.search("ifc zone")).toContain("archicad-export-quirk");
  });

  it("parks an offer and respects memory.enabled", async () => {
    expect(await m.offer({ title: "TOTEM export drops the bio-based flag", body: "Seen while exporting.", kind: "correction", target: "notes/40_LIBRARY/a.md" }))
      .toContain("augment_memory/offers/2026-09-27-totem-export-drops-the-bio-based-flag.md");
    const off = new Memory(repo, settingsFrom({ memory: { enabled: false } }), () => NOW, BY);
    await expect(off.add({ type: "tool", title: "x", summary: "y" })).rejects.toThrow(/disabled/);
  });

  it("agrees with its own token measure on a card read back", async () => {
    await m.add({ type: "tool", title: "Card one here", summary: "first summary line", keywords: "alpha" });
    const [c] = await m.cards();
    expect(cardTokens(c.fm)).toEqual(tokens("Card one here first summary line alpha"));
  });
});

describe("vault", () => {
  it("reads the wiki and in-scope sources, and refuses the rest with the reason", async () => {
    const repo = vaultRepo({
      "augment_wiki/concept/pace-layering.md": "---\ntype: concept\n---\nWiki.",
      "notes/40_LIBRARY/Pace layering.md": "---\naugment: \"#processed\"\n---\nSource.",
      "notes/40_LIBRARY/Tagged.md": "---\naugment: \"#excluded\"\n---\nNo.",
      "notes/40_LIBRARY/Excluded thing.md": "No.",
      "notes/40_LIBRARY/private/x.md": "No.",
      "notes/_inbox/y.md": "No.",
      "notes/NEW/z.md": "No.",
    });
    expect(await vault.read(repo, "augment_wiki/concept/pace-layering.md")).toContain("Wiki.");
    expect(await vault.read(repo, "notes/40_LIBRARY/Pace layering.md")).toContain("Source.");
    await expect(vault.read(repo, "notes/40_LIBRARY/Tagged.md")).rejects.toThrow(/#excluded/);
    await expect(vault.read(repo, "notes/40_LIBRARY/Excluded thing.md")).rejects.toThrow(/#excluded/);
    await expect(vault.read(repo, "notes/40_LIBRARY/private/x.md")).rejects.toThrow(/rules out of scope/);
    await expect(vault.read(repo, "notes/_inbox/y.md")).rejects.toThrow(/ignores/);
    await expect(vault.read(repo, "notes/NEW/z.md")).rejects.toThrow(/not ruled on/);
    await expect(vault.read(repo, "notes/40_LIBRARY/../PERSONAL/d.md")).rejects.toThrow(/not a vault path/);
    await expect(vault.read(repo, "augment_wiki/config.yaml")).rejects.toThrow(/markdown/);
  });

  it("searches wiki titles and in-scope source paths only", async () => {
    const out = await vault.search(vaultRepo(), "pace layering");
    expect(out).toContain("augment_wiki/concept/pace-layering.md");
    expect(out).toContain("notes/40_LIBRARY/Pace layering.md");
    expect(out).not.toContain("PERSONAL");
    expect(out.indexOf("augment_wiki")).toBeLessThan(out.indexOf("notes/40_LIBRARY"));
  });

  it("captures into the inbox, create-only, marked by authorship", async () => {
    const repo = vaultRepo();
    const r = await vault.capture(repo, { title: "Site visit: roof / gutters", body: "Moss on the north slope.", authorship: "model", provenance: "Drafted from the person's voice memo." }, NOW, BY);
    expect(r).toContain("notes/_inbox/Site visit roof gutters.md");
    const text = (await repo.read("notes/_inbox/Site visit roof gutters.md"))!.text;
    expect(text).toBe(`---\naugment: "#to-process"\ncreated: ${NOW}\nupdated: ${NOW}\nassisted_by: ${BY}\n---\n\n# Site visit: roof / gutters\n\n> [!ai] ${BY}, 2026-09-27\n> Drafted from the person's voice memo.\n\nMoss on the north slope.\n`);
    await expect(vault.capture(repo, { title: "Site visit: roof / gutters", body: "again", authorship: "model" }, NOW, BY)).rejects.toThrow(/exists already/);
    await vault.capture(repo, { title: "My own words", body: "Mine.", authorship: "person" }, NOW, BY);
    const mine = (await repo.read("notes/_inbox/My own words.md"))!.text;
    expect(mine).not.toContain("assisted_by");
    expect(mine).not.toContain("[!ai]");
  });
});

describe("mcp", () => {
  const ctx = () => ({ repo: vaultRepo(), now: () => NOW, by: BY });
  const post = (body: unknown) => new Request("https://x/mcp", { method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json" } });

  it("initialises, lists tools, and answers a notification with 202", async () => {
    const init = await (await serve(post({ jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-06-18" } }), ctx())).json() as any;
    expect(init.result.protocolVersion).toBe("2025-06-18");
    expect(init.result.instructions).toMatch(/would this still matter/);
    const list = await (await serve(post({ jsonrpc: "2.0", id: 2, method: "tools/list" }), ctx())).json() as any;
    expect(list.result.tools.map((t: any) => t.name)).toEqual(TOOLS.map((t) => t.name));
    expect((await serve(post({ jsonrpc: "2.0", method: "notifications/initialized" }), ctx())).status).toBe(202);
    expect((await serve(new Request("https://x/mcp"), ctx())).status).toBe(405);
  });

  it("returns refusals as tool errors, and activates", async () => {
    const r = await (await serve(post({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "vault_read", arguments: { path: "notes/_inbox/y.md" } } }), ctx())).json() as any;
    expect(r.result.isError).toBe(true);
    expect(r.result.content[0].text).toMatch(/^REFUSED: /);
    const a = await (await serve(post([{ jsonrpc: "2.0", id: 4, method: "tools/call", params: { name: "activate", arguments: {} } }]), ctx())).json() as any;
    expect(a[0].result.content[0].text).toMatch(/commit abcdef1/);
  });
});
