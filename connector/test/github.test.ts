import { afterEach, describe, expect, it, vi } from "vitest";
import { GitHubRepo } from "../src/github";

afterEach(() => vi.unstubAllGlobals());

function stub(handler: (url: string, init: RequestInit) => Response) {
  const calls: { url: string; init: RequestInit }[] = [];
  vi.stubGlobal("fetch", async (url: string, init: RequestInit = {}) => { calls.push({ url, init }); return handler(url, init); });
  return calls;
}

describe("GitHubRepo", () => {
  const repo = () => new GitHubRepo("tok", "owner/vault", "main");

  it("encodes paths per segment and round-trips UTF-8 through base64", async () => {
    const text = "Déjà vu, ✓ and a line\n";
    let sent = "";
    const calls = stub((url, init) => {
      if (init.method === "PUT") { sent = JSON.parse(String(init.body)).content; return new Response("{}", { status: 201 }); }
      const content = btoa(String.fromCharCode(...new TextEncoder().encode(text)));
      return Response.json({ type: "file", sha: "s1", content, encoding: "base64" });
    });
    const f = await repo().read("notes/40 LIB/Pace #1.md");
    expect(calls[0].url).toBe("https://api.github.com/repos/owner/vault/contents/notes/40%20LIB/Pace%20%231.md?ref=main");
    expect(f).toEqual({ path: "notes/40 LIB/Pace #1.md", sha: "s1", text });
    expect(await repo().write("a/b.md", text, "msg")).toBe("ok");
    expect(new TextDecoder().decode(Uint8Array.from(atob(sent), (c) => c.charCodeAt(0)))).toBe(text);
    expect((calls[1].init.headers as Record<string, string>).Authorization).toBe("Bearer tok");
  });

  it("maps an existing path to exists and a stale sha to conflict", async () => {
    stub(() => new Response("{}", { status: 422 }));
    expect(await repo().write("a.md", "x", "m")).toBe("exists");
    expect(await repo().write("a.md", "x", "m", "old")).toBe("conflict");
    stub(() => new Response("{}", { status: 409 }));
    expect(await repo().write("a.md", "x", "m", "old")).toBe("conflict");
  });

  it("reads a folder's notes in one GraphQL request, and a missing folder as empty", async () => {
    const calls = stub(() => Response.json({ data: { repository: { object: { entries: [
      { name: "b.md", type: "blob", oid: "2", object: { text: "B" } },
      { name: "a.md", type: "blob", oid: "1", object: { text: "A" } },
      { name: "img.png", type: "blob", oid: "3", object: { text: null } },
      { name: "sub", type: "tree", oid: "4", object: null }] } } } }));
    expect(await repo().readDir("augment_memory/card")).toEqual([
      { path: "augment_memory/card/a.md", sha: "1", text: "A" }, { path: "augment_memory/card/b.md", sha: "2", text: "B" }]);
    expect(calls).toHaveLength(1);
    expect(JSON.parse(String(calls[0].init.body)).variables.e).toBe("main:augment_memory/card");
    stub(() => Response.json({ data: { repository: { object: null } } }));
    expect(await repo().readDir("augment_memory/card")).toEqual([]);
  });

  it("treats a missing file as absent", async () => {
    stub(() => new Response("", { status: 404 }));
    expect(await repo().read("nope.md")).toBeNull();
  });
});
