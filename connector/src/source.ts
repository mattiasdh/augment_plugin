/**
 * The system's two writes into a person's source note, ported from the plugin's
 * `scripts/source_write.py` (`set` and `callout`) and `scripts/hash_source.py`, so
 * a write through the connector is byte for byte the write Tier 1 and Tier 2 make.
 * The parity tests run the Python on the same fixtures and compare.
 *
 * Text here is the file decoded as UTF-8 with its BOM kept, so a string line is a
 * byte line: "\r" stays at the end of a CRLF line and is written back as it was.
 */

const DECL = /^(Status|augment|wiki|created|updated|assisted_by):/;
const BOM = "﻿";
export const KEYS = ["augment", "created", "updated", "assisted_by"] as const;

function lstripBom(s: string): string {
  let i = 0;
  while (s.startsWith(BOM, i)) i += 1;
  return s.slice(i);
}

function split(raw: string): [string[], boolean] {
  const trailing = raw.endsWith("\n");
  const lines = raw.split("\n");
  if (trailing) lines.pop();
  return [lines, trailing];
}

function join(lines: string[], trailing: boolean): string {
  return lines.join("\n") + (trailing ? "\n" : "");
}

function fence(lines: string[]): [number, number] | null {
  if (lines.length && lstripBom(lines[0]).replace(/\r+$/, "") === "---") {
    for (let j = 1; j < lines.length; j++) {
      const l = lines[j].replace(/\r+$/, "");
      if (l === "---" || l === "...") return [0, j];
    }
  }
  return null;
}

const value = (key: string, v: string) => (key === "augment" ? `augment: "${v}"` : `${key}: ${v}`);
const keyPat = (key: string) => new RegExp(`^${key}:`);

/** `raw` with system key `key` set to `value`; the body is left as it was. */
export function setKey(raw: string, key: string, v: string): string {
  let [lines, trailing] = split(raw);
  const pat = keyPat(key);
  const f = fence(lines);
  if (f) {
    const close = f[1];
    const block = lines.slice(1, close);
    const near = block.find((l) => DECL.test(l)) ?? lines[0];
    const cr = near.endsWith("\r") ? "\r" : "";
    const nw = value(key, v) + cr;
    const k = block.findIndex((l) => pat.test(l));
    if (k >= 0) {
      if (block[k] === nw) return raw;
      block[k] = nw;
    } else if (key === "augment") {
      block.unshift(nw);
    } else {
      let last = -1;
      block.forEach((l, i) => { if (DECL.test(l)) last = i; });
      if (last < 0) last = block.length - 1;
      block.splice(last + 1, 0, nw);
    }
    return join([...lines.slice(0, 1), ...block, ...lines.slice(close)], trailing);
  }
  let lead = 0;
  while (lead < lines.length && DECL.test(lstripBom(lines[lead]))) lead++;
  const decl = lines.slice(0, lead);
  const first = decl.length ? decl[0] : (lines.length ? lines[0] : "");
  const cr = first.endsWith("\r") ? "\r" : "";
  const nw = value(key, v) + cr;
  const k = decl.findIndex((l) => pat.test(lstripBom(l)));
  if (k >= 0) decl[k] = nw;
  else if (key === "augment") decl.unshift(nw);
  else decl.push(nw);
  const body = lines.slice(lead);
  if (!trailing && !body.length && !lines.length) trailing = true;
  return join(["---" + cr, ...decl, "---" + cr, ...body], trailing);
}

/** The callout placed after the `# Title` (or at the head of `heading`), with the indices of the inserted lines. */
export function insertCallout(raw: string, kind: "ai" | "note", actor: string, date: string, text: string, heading?: string): [string, number[]] {
  if (text.includes("\n") || text.includes("\r")) throw new Error("callout text must be one paragraph on one line");
  const [lines, trailing] = split(raw);
  const f = fence(lines);
  const start = f ? f[1] + 1 : 0;
  let at: number;
  if (heading) {
    const target = heading.trim();
    at = -1;
    for (let i = start; i < lines.length; i++) if (lines[i].replace(/\r+$/, "").trim() === target) { at = i; break; }
    if (at < 0) throw new Error(`heading not found: ${heading}`);
  } else {
    at = -1;
    for (let i = start; i < lines.length; i++) if (lines[i].startsWith("# ")) { at = i; break; }
    if (at < 0) at = start - 1;
  }
  const near = at >= 0 && at < lines.length ? lines[at] : (start < lines.length ? lines[start] : "");
  const cr = near.endsWith("\r") ? "\r" : "";
  const block = ["" + cr, `> [!${kind}] ${actor}, ${date}` + cr, `> ${text}` + cr];
  const rest = lines.slice(at + 1);
  if (rest.length && rest[0].replace(/^[ \t\r]+|[ \t\r]+$/g, "")) block.push("" + cr);
  const out = [...lines.slice(0, at + 1), ...block, ...rest];
  return [join(out, trailing), block.map((_, i) => at + 1 + i)];
}

/** The body lines the content hash covers, as hash_source.body_lines takes them. */
function bodyLines(raw: string): string[] {
  const seg = raw.split("\n");
  if (raw.endsWith("\n")) seg.pop();
  let i = 0;
  if (seg.length && lstripBom(seg[0]).replace(/\r+$/, "") === "---") {
    for (let j = 1; j < seg.length; j++) {
      const l = seg[j].replace(/\r+$/, "");
      if (l === "---" || l === "...") { i = j + 1; break; }
    }
  }
  while (i < seg.length && DECL.test(lstripBom(seg[i]))) i++;
  while (i < seg.length && !seg[i].replace(/[ \t\r]/g, "")) i++;
  return seg.slice(i);
}

export async function contentHash(raw: string): Promise<string> {
  const body = bodyLines(raw).map((l) => l + "\n").join("");
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(body));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 8);
}

export class SourceRefused extends Error {}

/** A status or metadata write: refused when it would move the content hash. Returns null when unchanged. */
export async function writeKey(raw: string, key: string, v: string): Promise<string | null> {
  if (!(KEYS as readonly string[]).includes(key)) throw new SourceRefused(`${key} is not a system key; only ${KEYS.join(", ")} are written`);
  const out = setKey(raw, key, v);
  if (out === raw) return null;
  if ((await contentHash(out)) !== (await contentHash(raw))) throw new SourceRefused("the write would move the content hash");
  return out;
}

/** A comment: refused when removing the inserted lines does not give back the original. Stamps `updated:`. */
export function writeCallout(raw: string, kind: "ai" | "note", actor: string, date: string, text: string, stamp: string, heading?: string): string {
  let out: string, added: number[];
  try { [out, added] = insertCallout(raw, kind, actor, date, text, heading); }
  catch (e) { throw new SourceRefused((e as Error).message); }
  const [lines, trailing] = split(out);
  const drop = new Set(added);
  if (join(lines.filter((_, i) => !drop.has(i)), trailing) !== raw) throw new SourceRefused("the insert would alter existing text");
  return setKey(out, "updated", stamp);
}
