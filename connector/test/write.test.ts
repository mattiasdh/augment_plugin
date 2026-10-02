import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import { contentHash, insertCallout, setKey } from "../src/source";
import * as vault from "../src/vault";
import * as w from "../src/write";
import { Memory, settingsFrom } from "../src/memory";
import { CONFIG, FakeRepo, INDEX } from "./fake";

const SCRIPTS = join(__dirname, "..", "..", "scripts");
const NOW = "2026-10-03 09:15";
const BY = "augment/connector";

function python(code: string, input: string): string | null {
  try { return execFileSync("python3", ["-c", code], { cwd: SCRIPTS, encoding: "utf-8", input }); } catch { return null; }
}
const havePython = existsSync(join(SCRIPTS, "source_write.py")) && python("import yaml", "") !== null;

const FIXTURES: Record<string, string> = {
  fenced: "---\naugment: \"#processed\"\ncreated: 2026-01-01\nupdated: 2026-01-02\ntags: [x]\n---\n# Title\n\nBody line.\n## Budget\nNumbers.\n",
  crlf: "---\r\naugment: \"#processed\"\r\nupdated: 2026-01-02\r\n---\r\n# Titre\r\n\r\nCorps.\r\n",
  bom: "﻿---\naugment: \"#to-process\"\n---\n# BOM note\nText right after the title.\n",
  bare: "augment: \"#processed\"\nupdated: 2026-01-02\n\n# Bare form\n\nBody.\n",
  plain: "# No frontmatter\n\nJust text.",
  untitled: "---\ncreated: 2026-01-01\n---\nNo title line at all.\n",
  empty: "",
};

describe.runIf(havePython)("source writes agree with source_write.py byte for byte", () => {
  const cases: [string, string, string][] = [["augment", "#excluded", ""], ["updated", "2026-10-03 09:15", ""], ["assisted_by", "augment/connector", ""]];
  it("sets system keys", () => {
    const want = JSON.parse(python(`import json, sys, source_write as S
fx = json.load(sys.stdin)
out = {}
for name, raw in fx.items():
    for k, v in ${JSON.stringify(cases.map(([k, v]) => [k, v]))}:
        out[name + ":" + k] = S.set_key(raw.encode("utf-8"), k, v).decode("utf-8")
print(json.dumps(out))`, JSON.stringify(FIXTURES))!);
    for (const [name, raw] of Object.entries(FIXTURES)) for (const [k, v] of cases) expect(setKey(raw, k, v), `${name}:${k}`).toBe(want[`${name}:${k}`]);
  });

  it("places callouts", () => {
    const calls: [string, string | null][] = Object.keys(FIXTURES).filter((n) => n !== "empty").map((n) => [n, null]);
    calls.push(["fenced", "## Budget"]);
    const want = JSON.parse(python(`import json, sys, source_write as S
fx = json.load(sys.stdin)
out = []
for name, heading in json.loads(${JSON.stringify(JSON.stringify(calls))}):
    raw, added = S.insert_callout(fx[name].encode("utf-8"), "ai", "augment/connector", "2026-10-03", "One observation.", heading)
    out.append([raw.decode("utf-8"), added])
print(json.dumps(out))`, JSON.stringify(FIXTURES))!);
    calls.forEach(([name, heading], i) => {
      expect(insertCallout(FIXTURES[name], "ai", "augment/connector", "2026-10-03", "One observation.", heading ?? undefined), `${name} ${heading ?? ""}`).toEqual(want[i]);
    });
  });

  it("hashes as hash_source.py does", async () => {
    const want = JSON.parse(python(`import json, sys, hash_source as H
print(json.dumps({k: H.content_hash_bytes(v.encode("utf-8")) for k, v in json.load(sys.stdin).items()}))`, JSON.stringify(FIXTURES))!);
    for (const [name, raw] of Object.entries(FIXTURES)) expect(await contentHash(raw), name).toBe(want[name]);
  });
});

function repoWith(extra: Record<string, string> = {}) {
  return new FakeRepo({ "augment_wiki/config.yaml": CONFIG + "author: mdh\n", "augment_wiki/index.jsonl": INDEX, ...extra });
}

describe("the connector's column of surfaces.md", () => {
  beforeEach(() => vault.clearCache());

  it("comments on a source without altering a byte, and parks the ledger entry in the same commit", async () => {
    const repo = repoWith({ "notes/40_LIBRARY/Pace layering.md": FIXTURES.fenced });
    const out = await w.sourceCallout(repo, { path: "notes/40_LIBRARY/Pace layering.md", text: "Brand's later book narrows this." }, NOW, BY);
    expect(out).toMatch(/commented on .* \(hash \w{8} -> \w{8}\)/);
    const text = repo.files.get("notes/40_LIBRARY/Pace layering.md")!.text;
    expect(text).toContain("# Title\n\n> [!ai] augment/connector, 2026-10-03\n> Brand's later book narrows this.\n\nBody line.");
    expect(text).toContain("updated: 2026-10-03 09:15");
    const pending = [...repo.files.keys()].filter((p) => p.startsWith("augment_wiki/history.pending/"));
    expect(pending).toHaveLength(1);
    expect(JSON.parse(repo.files.get(pending[0])!.text)).toMatchObject({ kind: "comment_run", source: "notes/40_LIBRARY/Pace layering.md" });
    expect(repo.commits).toHaveLength(1);
    await w.sourceCallout(repo, { path: "notes/40_LIBRARY/Pace layering.md", text: "Dictated.", kind: "note", heading: "## Budget" }, NOW, BY);
    expect(repo.files.get("notes/40_LIBRARY/Pace layering.md")!.text).toContain("## Budget\n\n> [!note] mdh, 2026-10-03\n> Dictated.\n\nNumbers.");
  });

  it("sets a status without moving the hash, and refuses what is not a system key", async () => {
    const repo = repoWith({ "notes/40_LIBRARY/a.md": FIXTURES.crlf });
    expect(await w.sourceSet(repo, { path: "notes/40_LIBRARY/a.md", key: "augment", value: "#excluded" }, BY)).toBe("set augment on notes/40_LIBRARY/a.md");
    expect(repo.files.get("notes/40_LIBRARY/a.md")!.text).toBe(FIXTURES.crlf.replace('"#processed"', '"#excluded"'));
    await expect(w.sourceSet(repo, { path: "notes/40_LIBRARY/a.md", key: "tags", value: "x" }, BY)).rejects.toThrow(/not a system key/);
    await expect(w.sourceSet(repo, { path: "notes/40_LIBRARY/a.md", key: "augment", value: "excluded" }, BY)).rejects.toThrow(/not a valid/);
    await expect(w.sourceSet(repo, { path: "augment_wiki/concept/x.md", key: "augment", value: "#x" }, BY)).rejects.toThrow(/not a source/);
  });

  it("creates notes where a note may be created, and never replaces a source", async () => {
    const repo = repoWith({ "notes/40_LIBRARY/a.md": "---\naugment: \"#processed\"\n---\nOld." });
    const note = "---\naugment: \"#to-process\"\ncreated: 2026-10-03 09:15\nupdated: 2026-10-03 09:15\n---\n# New\n\nText.\n";
    expect(await w.write(repo, { path: "notes/40_LIBRARY/New.md", content: note }, "2026-10-03", BY)).toMatch(/^created/);
    await expect(w.write(repo, { path: "notes/40_LIBRARY/a.md", content: note }, "2026-10-03", BY)).rejects.toThrow(/append-only/);
    await expect(w.write(repo, { path: "notes/40_LIBRARY/Bare.md", content: "# No frontmatter" }, "2026-10-03", BY)).rejects.toThrow(/declaration/);
    await expect(w.write(repo, { path: "augment_memory/card/x.md", content: "x" }, "2026-10-03", BY)).rejects.toThrow(/memory tools/);
    await expect(w.write(repo, { path: "notes/40_LIBRARY/private/x.md", content: note }, "2026-10-03", BY)).rejects.toThrow(/rules out of scope/);
    await expect(w.write(repo, { path: "notes/NEW/x.md", content: note }, "2026-10-03", BY)).rejects.toThrow(/not ruled on/);
    await expect(w.write(repo, { path: "augment_wiki/index.jsonl", content: "{}" }, "2026-10-03", BY)).rejects.toThrow(/markdown/);
    expect(await w.write(repo, { path: "augment_wiki/concept/new.md", content: "---\ntype: concept\n---\n# New\n" }, "2026-10-03", BY)).toMatch(/compiled output/);
  });

  it("edits a skill reference once, with its CHANGELOG line, in one commit", async () => {
    const repo = repoWith({
      "notes/ASSETS/skills/aa-socials/references/VOICE.md": "Never write journey.\nUse figures.\n",
      "notes/ASSETS/skills/aa-socials/CHANGELOG.md": "# aa-socials changelog\n\nIntro.\n\n- 2026-10-02: moved into the vault.\n",
    });
    const n = repo.commits.length;
    await expect(w.edit(repo, { path: "notes/ASSETS/skills/aa-socials/references/VOICE.md", old: "Use figures.", new: "Use figures, with their source." }, "2026-10-03", BY))
      .rejects.toThrow(/CHANGELOG line/);
    expect(await w.edit(repo, { path: "notes/ASSETS/skills/aa-socials/references/VOICE.md", old: "Use figures.", new: "Use figures, with their source.", changelog: "figures carry their source" }, "2026-10-03", BY))
      .toMatch(/with its CHANGELOG line/);
    expect(repo.commits.length).toBe(n + 1);
    expect(repo.files.get("notes/ASSETS/skills/aa-socials/references/VOICE.md")!.text).toBe("Never write journey.\nUse figures, with their source.\n");
    expect(repo.files.get("notes/ASSETS/skills/aa-socials/CHANGELOG.md")!.text)
      .toBe("# aa-socials changelog\n\nIntro.\n\n- 2026-10-03: figures carry their source (references/VOICE.md)\n- 2026-10-02: moved into the vault.\n");
    await expect(w.edit(repo, { path: "notes/ASSETS/skills/aa-socials/references/VOICE.md", old: "absent", new: "x", changelog: "c" }, "2026-10-03", BY)).rejects.toThrow(/not in/);
    await expect(w.edit(repo, { path: "notes/40_LIBRARY/a.md", old: "a", new: "b" }, "2026-10-03", BY)).rejects.toThrow(/append-only/);
  });

  it("lists what the reading rules open, and names closed folders", async () => {
    const repo = repoWith({ "notes/40_LIBRARY/a.md": "x", "notes/40_LIBRARY/private/b.md": "x", "notes/_inbox/c.md": "x", "notes/NEW/d.md": "x" });
    const out = await w.list(repo, "notes");
    expect(out).toContain("notes/40_LIBRARY/");
    expect(out).toContain("notes/NEW/  (closed: not ruled on yet)");
    expect(out).toContain("notes/_inbox/");
    expect(await w.list(repo, "notes/40_LIBRARY")).toBe("notes/40_LIBRARY/private/  (closed: ruled out of scope)\nnotes/40_LIBRARY/a.md");
    await expect(w.list(repo, "notes/NOPE")).rejects.toThrow(/no folder/);
  });

  it("parks ledger entries and refuses malformed ones", async () => {
    const repo = repoWith();
    expect(await w.appendHistory(repo, [{ id: "notes/x.md", event: "flag" }], NOW, BY)).toMatch(/history\.pending\/202610030915-\w+\.jsonl/);
    await expect(w.appendHistory(repo, [{ event: "no id" }], NOW, BY)).rejects.toThrow(/string id/);
  });

  it("writes a memory card and its index in one commit, and refuses a stale head", async () => {
    const repo = repoWith();
    const m = new Memory(repo, settingsFrom({}), () => NOW, BY);
    await m.add({ type: "tool", title: "Coda canvas cells", summary: "Canvas cells via the per-cell URI" });
    expect(repo.commits).toEqual(["MEMORY: add coda-canvas-cells\n\nAssisted-by: augment/connector"]);
    expect(repo.files.get("augment_memory/index.md")!.text).toContain("Canvas cells via the per-cell URI");
    expect(await repo.commit([{ path: "x.md", text: "x" }], "stale", "not-the-head")).toBe("conflict");
  });
});
