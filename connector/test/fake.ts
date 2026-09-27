import type { Head, Repo, RepoFile } from "../src/github";

/** An in-memory repository with the same create-only and compare-and-swap rules as GitHub's contents API. */
export class FakeRepo implements Repo {
  files = new Map<string, { sha: string; text: string }>();
  commits: string[] = [];
  private n = 0;

  constructor(seed: Record<string, string> = {}) {
    for (const [p, t] of Object.entries(seed)) this.files.set(p, { sha: this.sha(), text: t });
  }

  private sha() { return `sha${++this.n}`; }

  async head(): Promise<Head> { return { oid: "abcdef1234567890", date: "2026-09-27T12:00:00Z" }; }

  async read(path: string): Promise<RepoFile | null> {
    const f = this.files.get(path);
    return f ? { path, sha: f.sha, text: f.text } : null;
  }

  async readDir(dir: string): Promise<RepoFile[]> {
    return [...this.files.entries()]
      .filter(([p]) => p.startsWith(dir + "/") && !p.slice(dir.length + 1).includes("/") && p.endsWith(".md"))
      .map(([p, f]) => ({ path: p, sha: f.sha, text: f.text }))
      .sort((a, b) => (a.path < b.path ? -1 : 1));
  }

  async write(path: string, text: string, message: string, sha?: string): Promise<"ok" | "exists" | "conflict"> {
    const cur = this.files.get(path);
    if (!sha && cur) return "exists";
    if (sha && (!cur || cur.sha !== sha)) return "conflict";
    this.files.set(path, { sha: this.sha(), text });
    this.commits.push(message);
    return "ok";
  }
}

export const CONFIG = `house_language: en
source_root: notes
memory:
  inject_chars: 6000
scope:
  ignore:
    - notes/_inbox
  rules:
    - path: "notes/40_LIBRARY"
      in_scope: true
      default: "#to-process"
    - path: "notes/40_LIBRARY/private"
      in_scope: false
    - path: "notes/PERSONAL"
      in_scope: false
    - path: "notes/PERSONAL/READING"
      in_scope: true
`;

export const INDEX = [
  { id: "augment_wiki/concept/pace-layering.md", type: "concept", kind: "model", title: "Pace layering orders change by speed", status: "#current" },
  { id: "notes/40_LIBRARY/Pace layering.md", status: "processed" },
  { id: "notes/40_LIBRARY/Excluded thing.md", status: "excluded" },
  { id: "notes/40_LIBRARY/Old name.md", status: "renamed", renamed_to: "notes/40_LIBRARY/New name.md" },
  { id: "notes/PERSONAL/Diary pace.md", status: "processed" },
].map((e) => JSON.stringify(e)).join("\n") + "\n";
