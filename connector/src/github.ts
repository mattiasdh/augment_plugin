/**
 * The vault repository, through GitHub's API. The only thing that talks to GitHub.
 *
 * The connector reads the repository as it stands on GitHub, so what the person
 * has edited in Obsidian and not yet pushed is not there; every answer says which
 * commit it read. Writes are single-file commits, create-only or checked against
 * the blob they replace, so a write never overwrites a change it did not see.
 */

export interface RepoFile { path: string; sha: string; text: string }
export interface Entry { name: string; path: string; type: "file" | "dir"; sha: string }
export interface Change { path: string; text: string }
export interface Head { oid: string; date: string }

/** What the tools need from a repository. The tests supply an in-memory one. */
export interface Repo {
  head(): Promise<Head>;
  read(path: string): Promise<RepoFile | null>;
  /** Every `.md` file directly inside `dir`, with its text, in one request. */
  readDir(dir: string): Promise<RepoFile[]>;
  /** Create when `sha` is absent (refused if the path exists), else replace that blob. */
  write(path: string, text: string, message: string, sha?: string): Promise<"ok" | "exists" | "conflict">;
  /** The file as its exact bytes allow: BOM kept, and null-safe refusal of anything that is not valid UTF-8. */
  readExact(path: string): Promise<RepoFile | null>;
  /** The entries directly inside `dir`, files and folders, or null when there is no such folder. */
  list(dir: string): Promise<Entry[] | null>;
  /** Several files in one commit, refused ("conflict") when the branch moved past `expectedHead`. */
  commit(changes: Change[], message: string, expectedHead: string): Promise<"ok" | "conflict">;
}

const API = "https://api.github.com";

function b64encode(text: string): string {
  const bytes = new TextEncoder().encode(text);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(bin);
}

function b64bytes(b64: string): Uint8Array {
  const bin = atob(b64.replace(/\n/g, ""));
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return bytes;
}

function b64decode(b64: string): string {
  return new TextDecoder().decode(b64bytes(b64));
}

function encodePath(path: string): string {
  return path.split("/").map(encodeURIComponent).join("/");
}

export class GitHubRepo implements Repo {
  private owner: string;
  private name: string;

  constructor(private token: string, repo: string, private branch: string) {
    [this.owner, this.name] = repo.split("/");
    if (!this.owner || !this.name) throw new Error(`GITHUB_REPO must be OWNER/REPO, not ${repo}`);
  }

  private headers(accept = "application/vnd.github+json"): Record<string, string> {
    return {
      Authorization: `Bearer ${this.token}`,
      Accept: accept,
      "User-Agent": "augment-connector",
      "X-GitHub-Api-Version": "2022-11-28",
    };
  }

  private async graphql<T>(query: string, variables: Record<string, unknown>): Promise<T> {
    const r = await fetch(`${API}/graphql`, {
      method: "POST",
      headers: { ...this.headers(), "Content-Type": "application/json" },
      body: JSON.stringify({ query, variables }),
    });
    const j = (await r.json()) as { data?: T; errors?: { message: string }[] };
    if (!r.ok || j.errors?.length) throw new Error(`GitHub GraphQL: ${j.errors?.[0]?.message ?? r.status}`);
    return j.data as T;
  }

  async head(): Promise<Head> {
    const d = await this.graphql<{ repository: { ref: { target: { oid: string; committedDate: string } } | null } }>(
      `query($o:String!,$n:String!,$r:String!){repository(owner:$o,name:$n){ref(qualifiedName:$r){target{oid ... on Commit{committedDate}}}}}`,
      { o: this.owner, n: this.name, r: `refs/heads/${this.branch}` });
    const t = d.repository.ref?.target;
    if (!t) throw new Error(`no branch ${this.branch} in ${this.owner}/${this.name}`);
    return { oid: t.oid, date: t.committedDate };
  }

  async read(path: string): Promise<RepoFile | null> {
    const r = await fetch(`${API}/repos/${this.owner}/${this.name}/contents/${encodePath(path)}?ref=${encodeURIComponent(this.branch)}`,
      { headers: this.headers() });
    if (r.status === 404) return null;
    if (!r.ok) throw new Error(`GitHub read ${path}: ${r.status}`);
    const j = (await r.json()) as { type: string; sha: string; content?: string; encoding?: string; download_url?: string };
    if (j.type !== "file") return null;
    if (j.encoding === "base64" && j.content) return { path, sha: j.sha, text: b64decode(j.content) };
    // Over 1 MB the contents endpoint omits the body; fetch it raw.
    const raw = await fetch(`${API}/repos/${this.owner}/${this.name}/contents/${encodePath(path)}?ref=${encodeURIComponent(this.branch)}`,
      { headers: this.headers("application/vnd.github.raw+json") });
    if (!raw.ok) throw new Error(`GitHub raw read ${path}: ${raw.status}`);
    return { path, sha: j.sha, text: await raw.text() };
  }

  async readExact(path: string): Promise<RepoFile | null> {
    const r = await fetch(`${API}/repos/${this.owner}/${this.name}/contents/${encodePath(path)}?ref=${encodeURIComponent(this.branch)}`,
      { headers: this.headers() });
    if (r.status === 404) return null;
    if (!r.ok) throw new Error(`GitHub read ${path}: ${r.status}`);
    const j = (await r.json()) as { type: string; sha: string; content?: string; encoding?: string };
    if (j.type !== "file") return null;
    if (j.encoding !== "base64" || !j.content) throw new Error(`${path} is over 1 MB; the connector does not rewrite files that large`);
    // fatal: a file that is not valid UTF-8 is refused rather than written back with replacement characters.
    return { path, sha: j.sha, text: new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(b64bytes(j.content)) };
  }

  async list(dir: string): Promise<Entry[] | null> {
    const d = await this.graphql<{ repository: { object: { entries: { name: string; type: string; oid: string }[] } | null } }>(
      `query($o:String!,$n:String!,$e:String!){repository(owner:$o,name:$n){object(expression:$e){... on Tree{entries{name type oid}}}}}`,
      { o: this.owner, n: this.name, e: `${this.branch}:${dir}` });
    const entries = d.repository.object?.entries;
    if (!entries) return null;
    return entries
      .filter((e) => e.type === "blob" || e.type === "tree")
      .map((e) => ({ name: e.name, path: dir ? `${dir}/${e.name}` : e.name, type: e.type === "tree" ? "dir" as const : "file" as const, sha: e.oid }))
      .sort((a, b) => (a.type !== b.type ? (a.type === "dir" ? -1 : 1) : a.name < b.name ? -1 : 1));
  }

  async commit(changes: Change[], message: string, expectedHead: string): Promise<"ok" | "conflict"> {
    const [headline, ...rest] = message.split("\n");
    try {
      await this.graphql(
        `mutation($i:CreateCommitOnBranchInput!){createCommitOnBranch(input:$i){commit{oid}}}`,
        { i: {
          branch: { repositoryNameWithOwner: `${this.owner}/${this.name}`, branchName: this.branch },
          message: { headline, body: rest.join("\n").trim() || undefined },
          expectedHeadOid: expectedHead,
          fileChanges: { additions: changes.map((c) => ({ path: c.path, contents: b64encode(c.text) })) },
        } });
      return "ok";
    } catch (e) {
      if (/expected branch to point|expectedHeadOid/i.test(String((e as Error).message))) return "conflict";
      // Any other refusal of the mutation (a token or API change): fall back to one contents write per file,
      // each against the blob it replaces, so writes keep working without the single commit.
      if ((await this.head()).oid !== expectedHead) return "conflict";
      for (const c of changes) {
        const cur = await this.read(c.path);
        const r = await this.write(c.path, c.text, message, cur?.sha);
        if (r !== "ok") return "conflict";
      }
      return "ok";
    }
  }

  async readDir(dir: string): Promise<RepoFile[]> {
    const d = await this.graphql<{ repository: { object: { entries: { name: string; type: string; oid: string; object: { text: string | null } | null }[] } | null } }>(
      `query($o:String!,$n:String!,$e:String!){repository(owner:$o,name:$n){object(expression:$e){... on Tree{entries{name type oid object{... on Blob{text}}}}}}}`,
      { o: this.owner, n: this.name, e: `${this.branch}:${dir}` });
    const entries = d.repository.object?.entries ?? [];
    return entries
      .filter((e) => e.type === "blob" && e.name.endsWith(".md") && e.object?.text != null)
      .map((e) => ({ path: `${dir}/${e.name}`, sha: e.oid, text: e.object!.text as string }))
      .sort((a, b) => (a.path < b.path ? -1 : a.path > b.path ? 1 : 0));
  }

  async write(path: string, text: string, message: string, sha?: string): Promise<"ok" | "exists" | "conflict"> {
    const body: Record<string, string> = { message, content: b64encode(text), branch: this.branch };
    if (sha) body.sha = sha;
    const r = await fetch(`${API}/repos/${this.owner}/${this.name}/contents/${encodePath(path)}`, {
      method: "PUT",
      headers: { ...this.headers(), "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.ok) return "ok";
    if (!sha && r.status === 422) return "exists";
    if (r.status === 409 || r.status === 422) return "conflict";
    throw new Error(`GitHub write ${path}: ${r.status} ${(await r.text()).slice(0, 200)}`);
  }
}
