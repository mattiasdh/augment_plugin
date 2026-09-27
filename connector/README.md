# augment connector

A remote MCP server that reaches an augment vault through GitHub, for the surfaces that can run neither a shell nor a local MCP server: Claude on the web and the mobile apps. Desktop can use it too, when the Obsidian tier is not running. It runs as a Cloudflare Worker on the free plan.

**It carries the work that suits a phone: asking, remembering and capturing. Compiling stays where the scripts run.**

| Tool | Does | Tier 1 and 2 equivalent |
|---|---|---|
| `activate` | Confirms the vault is reachable, names the commit it reads, loads the memory cards that apply | the SessionStart hooks, or the `activate` skill |
| `memory_search`, `memory_get` | Find and read memory cards | `recall` |
| `memory_add`, `memory_seen`, `memory_update`, `memory_supersede` | Write memory, with the same duplicate, length and secret refusals as `memory_write.py` | `remember` |
| `memory_offer` | Parks content, a comment or a correction for the weekly sweep | `memory_write.py offer` |
| `vault_search` | Wiki notes by title, sources by path, from `augment_wiki/index.jsonl` | `answer`'s index step |
| `vault_read` | A wiki note, a memory file, or a source the scope rules allow | reading the file |
| `capture_note` | A new note in the inbox, create-only, marked `assisted_by:` and `[!ai]` when Claude drafted it | `write` capture |

What it does not do, by design:

- **No compiling.** `process`, `mint`, `dream` and `verify` need Python, git and the ledger, so they stay in Code, Cowork, Desktop's Tier 2 and the nightly routine.
- **No write into an existing note.** A comment or correction needs `source_write.py`, which never touches the person's text; the connector parks it with `memory_offer` instead, and the sweep applies it.
- **No full-text search of the sources.** The Worker may make 50 outbound calls per request on the free plan, so it searches the index (wiki titles, source paths) and reads notes one at a time.
- **It reads the last push.** Edits in Obsidian that Obsidian Git has not pushed yet are invisible, and `activate` says which commit was read. A short automatic push interval in Obsidian Git keeps the gap small.
- **The inbox is not readable**, since the vault's `config.yaml` ignores it. Captures land there and stay there until the sweep files them.

## What may be read

The vault's own `augment_wiki/config.yaml` decides, read at request time; nothing is hard-coded here. A source is readable when its scope rules put it in scope and it is not `#excluded`, in its frontmatter or in the index. A folder the config ignores, rules out, or has not ruled on stays closed, so a folder added tomorrow is closed until the sweep declares it. The wiki and the memory layer are readable whole, since both are written from what scope already allowed.

## Security model

- **Two credentials, two jobs.** Signing in with GitHub proves who is connecting and asks for no scope at all; the token from that sign-in is revoked as soon as the login is read. The vault is read and written with a separate **fine-grained personal access token** limited to the one repository, with Contents read and write and nothing else.
- **Only Claude receives tokens.** An OAuth client must redirect to a host in `ALLOWED_REDIRECT_HOSTS` (Claude's callback hosts by default), or authorisation is refused before GitHub is contacted.
- **Only you sign in.** The GitHub login must be in `ALLOWED_GITHUB_LOGINS`, checked at sign-in and again on every call, so removing a login locks it out at once.
- **Nothing is stored on Cloudflare** but the OAuth grants, in KV. Vault content passes through the Worker in transit only.
- **The repository holds client material**, so treat the Worker as a door into it: keep the PAT's expiry short enough to be rotated, and check Cloudflare's data processing terms against the office's GDPR obligations before relying on it.

## Setup

About twenty minutes, on a machine with Node 20 or later. The Worker's address exists only after the first deploy, and the GitHub OAuth app needs that address, so the order matters.

**1. Keep your settings out of this public repository.** Copy the config and work from the copy, which `.gitignore` excludes:

```bash
cd connector
npm install
cp wrangler.toml wrangler.local.toml
npx wrangler login
npx wrangler kv namespace create OAUTH_KV     # put the printed id in wrangler.local.toml
```

**2. Fill in `wrangler.local.toml`**: `GITHUB_REPO` (`owner/repo` of the vault), `ALLOWED_GITHUB_LOGINS` (your GitHub login), `TIMEZONE`, the IANA zone the vault's stamps are written in.

**3. First deploy**, to learn the address:

```bash
npx wrangler deploy -c wrangler.local.toml
```

Put the printed `https://augment-connector.<subdomain>.workers.dev` in `PUBLIC_URL`.

**4. Create the GitHub OAuth app** at GitHub, Settings, Developer settings, OAuth Apps, New: homepage `PUBLIC_URL`, callback `PUBLIC_URL/callback`. Copy the client id and generate a client secret.

**5. Create the fine-grained token** at GitHub, Settings, Developer settings, Fine-grained tokens: resource owner the vault's owner, **only the vault repository**, permission **Contents: Read and write** (Metadata read is added automatically), an expiry you will actually rotate.

**6. Store the three secrets and deploy again:**

```bash
npx wrangler secret put GITHUB_CLIENT_ID -c wrangler.local.toml
npx wrangler secret put GITHUB_CLIENT_SECRET -c wrangler.local.toml
npx wrangler secret put GITHUB_TOKEN -c wrangler.local.toml
npx wrangler deploy -c wrangler.local.toml
```

**7. Add it to Claude.** On a Team or Enterprise plan an Owner adds it under Organization settings, Connectors, Add, with the URL `PUBLIC_URL/mcp`; each member then connects it once under their own connector settings, which opens the GitHub sign-in. On an individual plan it is added under Customize, Connectors. A connector connected on the web is available on mobile after the next login there; Anthropic still describes custom connectors on mobile as beta, so test one capture from the phone before relying on it.

**8. Tell Claude when to use it.** Chat runs no hooks, so nothing loads the memory by itself. Either start a conversation with "activate augment", or add one line to your standing preferences, which load on every surface: *At the start of a conversation involving tools, files or the vault, call the augment connector's activate; record what you learn about how the work is done with memory_add.*

## Cost on the free plan

A tool call is one Worker request and one to three GitHub calls. The free plan allows 100,000 requests a day, so a day of heavy use is well under one percent of it. The Worker keeps the vault's config and index for a minute per instance, and reads the memory folder in a single GraphQL request.

## Development

```bash
npm test            # vitest; the parity tests run the plugin's Python beside the port
npm run typecheck
npx wrangler dev --var PUBLIC_URL:http://localhost:8787   # with a .dev.vars holding the three secrets
```

The memory rules are ported from `scripts/_memory.py` and `scripts/memory_write.py`, and the scope rules from `scripts/_gen_util.py`. The parity tests run those scripts and compare, so a change to either side that is not made on both fails the suite.
