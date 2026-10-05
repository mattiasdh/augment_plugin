/**
 * The MCP endpoint: JSON-RPC over HTTP POST, answered as JSON (the Streamable HTTP
 * transport without a stream, which the specification allows). Stateless, so no
 * session store and no Durable Object, which keeps the Worker on the free plan.
 */
import type { Repo } from "./github";
import { Memory, Refused, TYPES, settingsFrom } from "./memory";
import * as vault from "./vault";
import * as w from "./write";

export const VERSION = "0.1.0";
const PROTOCOLS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"];

const INSTRUCTIONS = `The augment vault and its memory, over GitHub. Start a conversation with activate, which reports the commit read and loads the memory cards that apply.
Before a task that names a tool, a file format, a client convention or a skill, call memory_search for it and open the cards that match with memory_get; apply them without asking, and name the card when it changes what you do.
A skill whose references live in the vault (under the skills root that config.yaml declares) reads them with vault_read on every use. A change to such a skill's rules, as the person's feedback on its output, is never a memory card: propose it, and park it with memory_offer kind correction and target the reference file's path; the weekly sweep applies it with the person.
Memory (memory_*) records how the work is done: how a tool, connector or MCP server really behaves, the person's file and output conventions, reusable snippets, working procedures. Test before writing: would this still matter if Claude were not involved? If yes it is content, not memory: offer it with capture_note (or memory_offer when the person is not there to confirm). Never store secrets, anyone else's personal data, or raw text copied from a page or file.
Memory is never evidence about projects, clients or the domain; vault_search and vault_read are, and the wiki notes cite their sources. Reads see the last push to GitHub, not unsynced edits in Obsidian.
Writes follow the same rules as every other surface (the plugin's rules/surfaces.md, Connector column): sources are append-only (source_callout, source_set), memory goes through memory_*, nothing is deleted or moved, closed folders stay closed. What needs the plugin's scripts (process, mint, dream, the sweep's checks) cannot run here: say so, and point to a Claude Code session on the vault, which runs them in full from the Claude app too.`;

type Args = Record<string, unknown>;
interface Tool { name: string; description: string; inputSchema: object; run: (a: Args, ctx: Ctx) => Promise<string> }
export interface Ctx { repo: Repo; now: () => string; by: string }

const str = (d: string) => ({ type: "string", description: d });
const strOrList = (d: string) => ({ anyOf: [{ type: "string" }, { type: "array", items: { type: "string" } }], description: d });

async function memory(ctx: Ctx): Promise<Memory> {
  return new Memory(ctx.repo, settingsFrom(await vault.loadConfig(ctx.repo)), ctx.now, ctx.by);
}

const s = (v: unknown) => (v === undefined || v === null ? undefined : String(v));

export const TOOLS: Tool[] = [
  {
    name: "activate",
    description: "Start of a conversation: confirms the vault is reachable, reports the commit the connector reads, and returns the memory cards that apply, project-scoped first. Call once at the start, and again after a long gap.",
    inputSchema: { type: "object", properties: { project: str("The project the conversation is about, as memory scopes name it (a repository or folder name). Optional.") } },
    async run(a, ctx) {
      const head = await ctx.repo.head();
      const m = await memory(ctx);
      const names = TOOLS.map((t) => t.name);
      return `AUGMENT CONNECTOR: vault read at commit ${head.oid.slice(0, 7)} (${head.date}). Reads see the last push to GitHub; edits not yet synced from Obsidian are not visible.\n` +
        `This connector serves ${names.length} tools: ${names.join(", ")}. If any of these is missing from your tool list, claude.ai holds a stale copy of the connector's tools: ask the person to reconnect it (Settings, Connectors) or to switch the missing tools on, and do not substitute another server's tool.\n` +
        (await m.context(s(a.project) ?? ""));
    },
  },
  {
    name: "memory_search",
    description: "Search the memory cards by the words that matter (tool, format, operation). Returns one line per card, best first. Use before working with a tool, connector or format a past session may have learned about.",
    inputSchema: { type: "object", required: ["query"], properties: {
      query: str("Words to look for."), type: { type: "string", enum: [...TYPES] }, scope: str("A project name; global cards are always included."),
      include_inactive: { type: "boolean", description: "Include superseded and archived cards." } } },
    async run(a, ctx) {
      return (await memory(ctx)).search(String(a.query ?? ""), { type: s(a.type), scope: s(a.scope), all: !!a.include_inactive });
    },
  },
  {
    name: "memory_get",
    description: "Read one memory card in full by its slug.",
    inputSchema: { type: "object", required: ["slug"], properties: { slug: str("The card's slug, as memory_search or activate lists it.") } },
    async run(a, ctx) { return (await memory(ctx)).get(String(a.slug ?? "")); },
  },
  {
    name: "memory_add",
    description: "Record something learned about how the work is done. Refused when an active card is already about the same thing (then use memory_seen or memory_update), and refused for anything that looks like a secret. Tell the person in one line what was recorded.",
    inputSchema: { type: "object", required: ["type", "title", "summary"], properties: {
      type: { type: "string", enum: [...TYPES], description: "tool: how a tool, connector, MCP server or program really behaves. preference: an output or file convention the person expects. snippet: a reusable script or command. procedure: a working sequence." },
      title: str("Ten words at most."),
      summary: str("One line of at most 160 characters that stands alone: it is what later sessions see without opening the card."),
      scope: strOrList("global, or the project names it applies to. Default global."),
      keywords: strOrList("A few retrieval words."),
      body: str("The mechanism in a few sentences, or the snippet in a fenced code block with one line on when to use it."),
      distinct: { type: "boolean", description: "Only when a near-duplicate refusal named a card that genuinely differs." } } },
    async run(a, ctx) {
      return (await memory(ctx)).add({ type: String(a.type ?? ""), title: String(a.title ?? ""), summary: String(a.summary ?? ""),
        scope: a.scope as string | string[] | undefined, keywords: a.keywords as string | string[] | undefined, body: s(a.body), distinct: !!a.distinct });
    },
  },
  {
    name: "memory_seen",
    description: "A card proved right in use, or the same thing was learned again: raises its seen count, which keeps it in the index.",
    inputSchema: { type: "object", required: ["slug"], properties: { slug: str("The card's slug.") } },
    async run(a, ctx) { return (await memory(ctx)).seen(String(a.slug ?? "")); },
  },
  {
    name: "memory_update",
    description: "Amend a card that is incomplete or slightly wrong. Only the fields given change; the body is replaced when one is given.",
    inputSchema: { type: "object", required: ["slug"], properties: {
      slug: str("The card's slug."), title: str("Ten words at most."), summary: str("One line, 160 characters at most."),
      type: { type: "string", enum: [...TYPES] }, scope: strOrList("global or project names."), keywords: strOrList("Retrieval words."), body: str("The new body.") } },
    async run(a, ctx) {
      return (await memory(ctx)).update(String(a.slug ?? ""), { title: s(a.title), summary: s(a.summary), type: s(a.type),
        scope: a.scope as string | string[] | undefined, keywords: a.keywords as string | string[] | undefined, body: s(a.body) });
    },
  },
  {
    name: "memory_supersede",
    description: "A card is wrong and a newer card replaces it: marks the old one superseded, pointing at the new. Add the new card first.",
    inputSchema: { type: "object", required: ["old", "new"], properties: { old: str("Slug of the card being replaced."), new: str("Slug of the card replacing it.") } },
    async run(a, ctx) { return (await memory(ctx)).supersede(String(a.old ?? ""), String(a.new ?? "")); },
  },
  {
    name: "memory_offer",
    description: "Park content found while working (a project fact, a decision, a comment on or correction of an existing note) for the weekly sweep, which moves it into the source layer. Use when the person is not there to confirm a capture_note, or for a comment or correction, which the connector cannot write into an existing note.",
    inputSchema: { type: "object", required: ["title", "body"], properties: {
      title: str("Ten words at most."), body: str("The drafted content."),
      kind: { type: "string", enum: ["capture", "comment", "correction"], description: "Default capture." },
      target: str("For a comment or correction: the path of the note it concerns.") } },
    async run(a, ctx) { return (await memory(ctx)).offer({ title: String(a.title ?? ""), body: String(a.body ?? ""), kind: s(a.kind), target: s(a.target) }); },
  },
  {
    name: "vault_search",
    description: "Find wiki notes by title, aliases (the names their Dutch or French sources use), keywords and summary, and in-scope sources by path. Search in any of the vault's languages. Read the hits with vault_read; a wiki note's sources: list leads to the sources behind it.",
    inputSchema: { type: "object", required: ["query"], properties: {
      query: str("Words a title or path would carry."), include_sources: { type: "boolean", description: "Also match source file paths. Default true." },
      limit: { type: "integer", minimum: 1, maximum: 50 } } },
    async run(a, ctx) { return vault.search(ctx.repo, String(a.query ?? ""), { sources: a.include_sources !== false, limit: a.limit as number | undefined }); },
  },
  {
    name: "vault_read",
    description: "Read a wiki note (augment_wiki/...), a memory file (augment_memory/...) or a source the vault's scope rules allow. Out-of-scope, unruled, ignored and #excluded sources are refused with the reason.",
    inputSchema: { type: "object", required: ["path"], properties: { path: str("The note's path from the vault root, ending in .md.") } },
    async run(a, ctx) { return vault.read(ctx.repo, String(a.path ?? "")); },
  },
  {
    name: "capture_note",
    description: "Write a new note into the inbox of the source layer, with the person's agreement. Create-only: it never touches an existing note. Model-drafted prose is marked as assisted; the person's own dictated words are not. Inbox notes stay unaddressed until the person files them.",
    inputSchema: { type: "object", required: ["title", "body", "authorship"], properties: {
      title: str("The note's title; it also names the file."), body: str("The note's content in markdown."),
      authorship: { type: "string", enum: ["model", "person"], description: "model: Claude drafted it. person: the person's own words, transcribed." },
      provenance: str("For model drafts: one line on what was drafted from what.") } },
    async run(a, ctx) {
      const authorship = a.authorship === "person" ? "person" : "model";
      return vault.capture(ctx.repo, { title: String(a.title ?? ""), body: String(a.body ?? ""), authorship, provenance: s(a.provenance) }, ctx.now(), ctx.by);
    },
  },
  {
    name: "vault_list",
    description: "List a folder: its notes and subfolders, as far as the reading rules open it. Closed folders are named with the reason, ignored ones not at all. Empty folder = the vault root.",
    inputSchema: { type: "object", properties: { folder: str("Folder path from the vault root, e.g. notes/20_COMM or augment_wiki/concept. Empty for the root.") } },
    async run(a, ctx) { return w.list(ctx.repo, String(a.folder ?? "")); },
  },
  {
    name: "vault_write",
    description: "Write a whole markdown note, as Tier 2's vault_write does, under the same rules (the plugin's rules/surfaces.md). Creates a new source note at an address the person named, or in the inbox (frontmatter with augment: \"#to-process\" included). Creates or replaces a wiki note only as part of process or mint, which need a script-capable surface for their ledger, so in practice rarely here. Creates or replaces a file under the skills root; a skill's references/ file needs the person's approval and a changelog line. Never replaces an existing source (source_callout, source_set), never writes augment_memory/ (memory tools), never a folder the config closes.",
    inputSchema: { type: "object", required: ["path", "content"], properties: {
      path: str("The note's path from the vault root, ending in .md."), content: str("The complete file, frontmatter included."),
      changelog: str("For a skill's references/ file: the one-line description of the approved rule change, logged in the skill's CHANGELOG.md in the same commit.") } },
    async run(a, ctx) { return w.write(ctx.repo, { path: String(a.path ?? ""), content: String(a.content ?? ""), changelog: s(a.changelog) }, ctx.now().slice(0, 10), ctx.by); },
  },
  {
    name: "vault_edit",
    description: "Replace one exact passage in a skill's file under the skills root (a rule change the person approved), so the rest of the file is never regenerated. The passage must occur exactly once. A references/ file takes a changelog line, committed with it. Sources, wiki notes and memory are refused with the route that applies.",
    inputSchema: { type: "object", required: ["path", "old", "new"], properties: {
      path: str("The file's path from the vault root."), old: str("The exact passage as it stands now."), new: str("Its replacement."),
      changelog: str("For a references/ file: one line on the approved change.") } },
    async run(a, ctx) { return w.edit(ctx.repo, { path: String(a.path ?? ""), old: String(a.old ?? ""), new: String(a.new ?? ""), changelog: s(a.changelog) }, ctx.now().slice(0, 10), ctx.by); },
  },
  {
    name: "source_set",
    description: "Set one system key of a source note's frontmatter, as source_write.py set does: augment (its state, e.g. #to-process or #excluded), created, updated or assisted_by. The person's own keys and the body are never touched, and the write is refused if it would move the content hash. Filing decisions are the person's: set a state only when they say so.",
    inputSchema: { type: "object", required: ["path", "key", "value"], properties: {
      path: str("The source's path from the vault root."), key: { type: "string", enum: ["augment", "created", "updated", "assisted_by"] },
      value: str("For augment, the tag with its #; dates as YYYY-MM-DD HH:MM.") } },
    async run(a, ctx) { return w.sourceSet(ctx.repo, { path: String(a.path ?? ""), key: String(a.key ?? ""), value: String(a.value ?? "") }, ctx.by); },
  },
  {
    name: "source_callout",
    description: "Comment on a source note, as source_write.py callout does (write skill, comment mode): a one-line > [!ai] callout for Claude's own observation, or > [!note] for the person's dictated words, placed after the title or at the head of a named section. Existing text is never altered (checked byte for byte), updated: is stamped, and the ledger entry is parked for the next compaction. Only when the person asks for the comment or confirms it.",
    inputSchema: { type: "object", required: ["path", "text"], properties: {
      path: str("The source's path from the vault root."), text: str("The comment, one paragraph on one line."),
      kind: { type: "string", enum: ["ai", "note"], description: "ai: Claude's observation (default). note: the person's own words." },
      heading: str("Optional: the exact section heading line (e.g. '## Budget') to comment at; default after the title.") } },
    async run(a, ctx) { return w.sourceCallout(ctx.repo, { path: String(a.path ?? ""), text: String(a.text ?? ""), kind: s(a.kind), heading: s(a.heading) }, ctx.now(), ctx.by); },
  },
  {
    name: "append_history",
    description: "Append entries to the ledger, as augment-runner's append_history does. GitHub cannot append to a file, so they are parked as one new file in augment_wiki/history.pending/, which compact_index.py merges into history.jsonl at the next script-capable run. Each entry is an object with a string id.",
    inputSchema: { type: "object", required: ["entries"], properties: { entries: { type: "array", items: { type: "object" } } } },
    async run(a, ctx) { return w.appendHistory(ctx.repo, a.entries, ctx.now(), ctx.by); },
  },
];

const BY_NAME = new Map(TOOLS.map((t) => [t.name, t]));

interface Msg { jsonrpc?: string; id?: string | number | null; method?: string; params?: Record<string, unknown> }

async function handle(msg: Msg, ctx: Ctx): Promise<object | null> {
  const id = msg.id;
  if (id === undefined || id === null) return null; // a notification
  const reply = (result: object) => ({ jsonrpc: "2.0", id, result });
  const error = (code: number, message: string) => ({ jsonrpc: "2.0", id, error: { code, message } });
  switch (msg.method) {
    case "initialize": {
      const asked = String(msg.params?.protocolVersion ?? "");
      return reply({
        protocolVersion: PROTOCOLS.includes(asked) ? asked : PROTOCOLS[1],
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: "augment-connector", version: VERSION },
        instructions: INSTRUCTIONS,
      });
    }
    case "ping":
      return reply({});
    case "tools/list":
      return reply({ tools: TOOLS.map(({ name, description, inputSchema }) => ({ name, description, inputSchema })) });
    case "tools/call": {
      const name = String(msg.params?.name ?? "");
      const tool = BY_NAME.get(name);
      if (!tool) return error(-32602, `unknown tool ${name}`);
      try {
        const text = await tool.run((msg.params?.arguments ?? {}) as Args, ctx);
        return reply({ content: [{ type: "text", text }], isError: false });
      } catch (e) {
        const text = e instanceof Refused ? `REFUSED: ${e.message}` : `ERROR: ${(e as Error).message}`;
        return reply({ content: [{ type: "text", text }], isError: true });
      }
    }
    default:
      return error(-32601, `method not found: ${msg.method}`);
  }
}

export async function serve(request: Request, ctx: Ctx): Promise<Response> {
  if (request.method !== "POST") {
    return new Response("This MCP endpoint answers POST only; it offers no event stream.", { status: 405, headers: { Allow: "POST" } });
  }
  let body: unknown;
  try { body = await request.json(); } catch {
    return Response.json({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "parse error" } }, { status: 400 });
  }
  const msgs: Msg[] = Array.isArray(body) ? (body as Msg[]) : [body as Msg];
  const batch = Array.isArray(body);
  const replies = (await Promise.all(msgs.map((m) => handle(m, ctx)))).filter((r): r is object => r !== null);
  if (!replies.length) return new Response(null, { status: 202 });
  return Response.json(batch ? replies : replies[0]);
}
