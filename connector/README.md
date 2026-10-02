# augment connector

A remote MCP server that reaches an augment vault through GitHub, for the surfaces that can run neither a shell nor a local MCP server: Claude on the web and the mobile apps. Desktop can use it too, when the Obsidian tier is not running. It runs as a Cloudflare Worker, a small program hosted in your own Cloudflare account, on the free plan.

**It has the same file primitives and the same rules as Tier 2 (the plugin's `rules/surfaces.md`, Connector column). What it lacks is the script runner, so compiling stays where the scripts run.**

| Tool | Does | Tier 1 and 2 equivalent |
|---|---|---|
| `activate` | Confirms the vault is reachable, names the commit it reads, loads the memory cards that apply | the SessionStart hooks, or the `activate` skill |
| `memory_search`, `memory_get` | Find and read memory cards | `recall` |
| `memory_add`, `memory_seen`, `memory_update`, `memory_supersede` | Write memory, with the same duplicate, length and secret refusals as `memory_write.py` | `remember` |
| `memory_offer` | Parks content, a comment or a correction for the weekly sweep | `memory_write.py offer` |
| `vault_search` | Wiki notes by title, aliases, keywords and summary, and sources by path, from `augment_wiki/search.json` (or `index.jsonl` on a vault without it) | `answer`'s index step |
| `vault_read` | A wiki note, a memory file, a skill's file under the declared skills root, or a source the scope rules allow | reading the file |
| `capture_note` | A new note in the inbox, create-only, marked `assisted_by:` and `[!ai]` when Claude drafted it | `write` capture |
| `vault_list` | A folder's notes and subfolders, as far as the reading rules open it; closed folders named with the reason | Obsidian's document map, `ls` |
| `vault_write` | A whole note: a new source at an address the person named or in the inbox, a wiki note, a skill file. Never replaces an existing source | Tier 2 `vault_write` |
| `vault_edit` | One exact passage of a skill's file replaced, with its CHANGELOG line, in one commit | `write` skill-rule edit |
| `source_set` | A source's `augment:`, `created:`, `updated:` or `assisted_by:`, refused if the content hash would move | `source_write.py set` |
| `source_callout` | A `[!ai]` or `[!note]` comment on a source, existing bytes untouched, `updated:` stamped, ledger entry parked | `source_write.py callout` |
| `append_history` | Ledger entries, parked in `augment_wiki/history.pending/` for `compact_index.py` to merge | `augment-runner` `append_history` |

What it does not do, by design:

- **No scripts.** `process`, `mint`, `dream` and the sweep's checks are built from the plugin's Python scripts, which a Worker cannot run, so they stay in Code (also from the Claude app, in the cloud), Cowork, Desktop's Tier 2 and the nightly routine.
- **No rewrite of the person's text**, the same rule every surface keeps: an existing source takes a comment (`source_callout`) or a status (`source_set`), both ports of `source_write.py` held to it by parity tests, and nothing else. No delete or move, and nothing into a folder the config closes.
- **Every write is one commit**, made against the head it read (GitHub's GraphQL `createCommitOnBranch`), so it never lands on top of a change it did not see. An unsynced edit in Obsidian to the same file meets it at the next pull, as it would from any other surface.
- **No full-text search of the sources.** The Worker may make 50 outbound calls per request on the free plan, so it searches `search.json` (wiki titles, aliases in the sources' own languages, keywords, one-line summaries, source paths) and reads notes one at a time. A capture whose title matches a note or source already there is still written, and the answer names the likely duplicates.
- **It reads the last push.** Edits in Obsidian that Obsidian Git has not pushed yet are invisible, and `activate` says which commit was read. A short automatic push interval in Obsidian Git keeps the gap small.
- **The inbox is not readable**, since the vault's `config.yaml` ignores it. Captures land there and stay there until the sweep files them.

## What may be read

The vault's own `augment_wiki/config.yaml` decides, read at request time; nothing is hard-coded here. A source is readable when its scope rules put it in scope and it is not `#excluded`, in its frontmatter or in the index. A folder the config ignores, rules out, or has not ruled on stays closed, so a folder added tomorrow is closed until the sweep declares it. The wiki and the memory layer are readable whole, since both are written from what scope already allowed. So is the skills root the config declares (`skills: root:`): it is ruled out of the wiki's scope, yet a skill reads its rules there on every use.

## Security model

- **Two credentials, two jobs.** Signing in with GitHub proves who is connecting and asks for no scope at all; the token from that sign-in is revoked as soon as the login is read. The vault is read and written with a separate **fine-grained personal access token** limited to the one repository, with Contents read and write and nothing else.
- **Only Claude receives tokens.** An OAuth client must redirect to a host in `ALLOWED_REDIRECT_HOSTS` (Claude's callback hosts by default), or authorisation is refused before GitHub is contacted.
- **Only you sign in.** The GitHub login must be in `ALLOWED_GITHUB_LOGINS`, checked at sign-in and again on every call, so removing a login locks it out at once.
- **Nothing is stored on Cloudflare** but the OAuth grants, in KV. Vault content passes through the Worker in transit only.
- **The repository holds client material**, so treat the Worker as a door into it: keep the PAT's expiry short enough to be rotated, and check Cloudflare's data processing terms against the office's GDPR obligations before relying on it.

## Setup

About half an hour the first time, and no prior Cloudflare experience is assumed.

### Where everything happens

**Nothing is installed or typed on Cloudflare's side.** You run a handful of commands in the Terminal on your own computer; one of them, `wrangler`, packs up the code in this folder and uploads it to your Cloudflare account, where it runs from then on. Your computer is only needed to set it up and to update it later; once deployed, the connector runs whether your computer is on or off.

| Where | What you do there |
|---|---|
| **Terminal on your computer** | Download this code, fill in one settings file, run `wrangler` to create, deploy and store secrets |
| **Cloudflare, in the browser** | Create a free account once; `wrangler` opens a browser page to connect to it. Nothing else is required, though the dashboard shows the running Worker and its logs. |
| **GitHub, in the browser** | Create a sign-in app and an access token for the vault repository |
| **Claude, in the browser** | Add the connector, then connect it once |

The steps below are written for a Mac. On Windows, use PowerShell and the Node.js installer for Windows; the commands are the same.

### What you need first

- **A Cloudflare account.** Sign up free at [dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up) and confirm the e-mail. The free plan is enough and asks for no payment details.
- **Node.js 20 or later**, which provides `npm` and `npx`. Check in Terminal with `node --version`. If the command is not found or the number is below 20, install the LTS version from [nodejs.org](https://nodejs.org), then open a new Terminal window.
- **git**, to download the code. `git --version` in Terminal either prints a version or offers to install the Apple command line tools; accept.
- **The GitHub account that owns the vault repository**, and, on a Team or Enterprise Claude plan, an Owner of the Claude organisation for step 11.

The order of the steps matters: the connector's web address exists only after the first deploy, and GitHub needs that address in step 7.

### 1. Download the code

In Terminal:

```bash
git clone https://github.com/mattiasdh/augment_plugin.git ~/augment_plugin
cd ~/augment_plugin/connector
npm install
```

`npm install` downloads the libraries the connector uses, `wrangler` among them, into this folder. Every later command is run from this folder; after closing Terminal, return to it with `cd ~/augment_plugin/connector`.

### 2. Make your private settings file

The repository is public, so your own values go into a copy that git ignores and never uploads:

```bash
cp wrangler.toml wrangler.local.toml
open -e wrangler.local.toml
```

This opens the file in TextEdit. Before typing, switch off Edit, Substitutions, Smart Quotes: curly quotes break the file. Any plain-text editor will do instead, or `nano wrangler.local.toml` inside Terminal. Leave the file open; steps 4 and 6 add to it.

Fill in the three values you already know, keeping the straight quotes:

- `GITHUB_REPO`: the vault repository as `owner/repo`, for example `"yourname/vault"`.
- `ALLOWED_GITHUB_LOGINS`: your GitHub user name. Only the logins listed here can ever connect.
- `TIMEZONE`: the zone the vault's timestamps are written in, for example `"Europe/Paris"`.

### 3. Connect wrangler to your Cloudflare account

```bash
npx wrangler login
```

A browser page opens at Cloudflare; log in and click Allow. Back in Terminal, `npx wrangler whoami` should print your account's e-mail.

### 4. Create the storage for sign-ins

```bash
npx wrangler kv namespace create OAUTH_KV
```

This creates a small key-value store in your Cloudflare account, where the connector keeps who is signed in. The output ends with a line holding `id = "…"`. Copy that id into `wrangler.local.toml`, replacing `REPLACE_WITH_THE_ID_FROM_wrangler_kv_namespace_create`, and save.

### 5. First deploy, to get the connector's address

```bash
npx wrangler deploy -c wrangler.local.toml
```

The `-c wrangler.local.toml` part tells wrangler to use your private file; every command from here carries it. If wrangler asks you to choose a `workers.dev` subdomain, pick a short name: it becomes part of the address. The output ends with the address, of the form `https://augment-connector.<your-subdomain>.workers.dev`.

The connector is now online but not yet usable, which is expected.

### 6. Put the address in the settings

In `wrangler.local.toml`, set `PUBLIC_URL` to that address exactly, with no slash at the end. Save. It is deployed again in step 9.

### 7. Create the GitHub sign-in app

In the browser, go to GitHub, Settings, Developer settings, OAuth Apps ([github.com/settings/developers](https://github.com/settings/developers)), and click New OAuth App:

- Application name: `augment connector`, or anything you will recognise.
- Homepage URL: your `PUBLIC_URL`.
- Authorization callback URL: your `PUBLIC_URL` followed by `/callback`.

Click Register application. On the next page, copy the **Client ID**, then click Generate a new client secret and copy the **secret**. GitHub shows the secret once only, so keep the page open until step 9.

This app is only how you prove to the connector who you are. It asks GitHub for no permissions.

### 8. Create the token the connector reads and writes with

Go to GitHub, Settings, Developer settings, Fine-grained tokens ([github.com/settings/personal-access-tokens/new](https://github.com/settings/personal-access-tokens/new)):

- Token name: `augment connector`.
- Expiration: a date you will act on, and a calendar reminder a week before it. When it expires the connector stops until step 9 is repeated for `GITHUB_TOKEN`.
- Resource owner: the owner of the vault repository.
- Repository access: **Only select repositories**, and select the vault repository alone.
- Permissions, Repository permissions: **Contents: Read and write**. Metadata read-only is added by itself. Leave everything else at No access.

Click Generate token and copy it. It too is shown once.

### 9. Store the three secrets, and deploy again

Each command asks you to paste a value; nothing appears as you paste, which is normal. Press Enter after each.

```bash
npx wrangler secret put GITHUB_CLIENT_ID -c wrangler.local.toml       # the Client ID from step 7
npx wrangler secret put GITHUB_CLIENT_SECRET -c wrangler.local.toml   # the client secret from step 7
npx wrangler secret put GITHUB_TOKEN -c wrangler.local.toml           # the token from step 8
npx wrangler deploy -c wrangler.local.toml
```

The secrets are stored encrypted in your Cloudflare account and never in a file on your computer, so nothing secret sits in `wrangler.local.toml`.

### 10. Check it is alive

Open your `PUBLIC_URL` in the browser: a short page titled "augment connector" should appear. Then, in Terminal:

```bash
curl -i -X POST https://augment-connector.<your-subdomain>.workers.dev/mcp
```

A `401 Unauthorized` answer is the right one: the connector is up and refuses anyone who has not signed in.

### 11. Add it to Claude

On a **Team or Enterprise** plan an Owner goes to Organization settings, Connectors, Add custom connector, gives it a name and the URL `PUBLIC_URL/mcp` (your address followed by `/mcp`), and saves. Each member then connects it once from their own connector settings (Customize, Connectors). On an **individual** plan, add it yourself under Customize, Connectors, Add custom connector.

Connecting sends you to GitHub, which asks once whether to authorise the app from step 7; after that you are back in Claude with the connector connected. A GitHub account not listed in `ALLOWED_GITHUB_LOGINS` gets a "Not allowed" page instead.

A connector connected on the web is available in the mobile apps after the next login there. Anthropic still describes custom connectors on mobile as beta, so make one test capture from the phone before relying on it.

### 12. Tell Claude when to use it

Chat runs no hooks, so nothing loads the memory by itself. Either start a conversation with "activate augment", or add one line to your standing preferences, which load on every surface: *At the start of a conversation involving tools, files or the vault, call the augment connector's activate; record what you learn about how the work is done with memory_add.*

### Later

| To | Run, in `~/augment_plugin/connector` |
|---|---|
| Install a newer version of the connector | `git pull`, then `npm install` and `npx wrangler deploy -c wrangler.local.toml` |
| Replace an expiring token | `npx wrangler secret put GITHUB_TOKEN -c wrangler.local.toml` with the new token; no redeploy needed |
| Lock someone out, or change a setting | edit `wrangler.local.toml`, then `npx wrangler deploy -c wrangler.local.toml` |
| Watch what the connector is doing | `npx wrangler tail -c wrangler.local.toml` while using it from Claude |
| Remove it entirely | `npx wrangler delete -c wrangler.local.toml`, then delete the OAuth app and the token on GitHub and the connector in Claude |

Keep a copy of `wrangler.local.toml` somewhere safe: it holds no secrets, but it is the only record of your settings, and git deliberately does not keep it.

### When something goes wrong

- **The address shows a Cloudflare error page (1101).** Usually `PUBLIC_URL` is missing or has a trailing slash. Fix it, deploy again, and read `npx wrangler tail` output for the exact message.
- **"Client not allowed" during connecting.** The request did not come from Claude's own sign-in flow; add the connector from Claude's connector settings, not from a copied link.
- **"Not allowed" after the GitHub step.** The GitHub login you used is not in `ALLOWED_GITHUB_LOGINS`.
- **"Sign-in expired".** More than ten minutes passed between starting and finishing the connection; start again from Claude.
- **Connected, but every call answers `ERROR: GitHub …`.** The token from step 8 is expired, lacks Contents read and write, or was given access to a different repository than `GITHUB_REPO`.

## Cost on the free plan

A tool call is one Worker request and one to three GitHub calls. The free plan allows 100,000 requests a day, so a day of heavy use is well under one percent of it. A memory write costs two or three more, since it also regenerates `augment_memory/index.md`. The Worker keeps the vault's config, index and search index for five minutes per instance, so a change to the scope rules in `config.yaml` reaches it within five minutes of the push, and it reads the memory folder in a single GraphQL request.

**CPU.** The free plan allows 10 ms of CPU per request. A warm search takes under 1 ms; the first request after the cache expires parses the config and the search index and measured 7 to 10 ms on a comparable machine. `search.json` arrives already tokenised by `gen_search.py`, and only the three sections of `config.yaml` the connector reads are parsed, both to stay under the limit. If `npx wrangler tail` ever shows error 1102, *Worker exceeded resource limits*, on such a first request, the remedy is the Workers Paid plan (5 USD a month, 30 seconds of CPU per request), not a change to the vault.

## Development

```bash
npm test            # vitest; the parity tests run the plugin's Python beside the port
npm run typecheck
npx wrangler dev --var PUBLIC_URL:http://localhost:8787   # with a .dev.vars holding the three secrets
```

The memory rules are ported from `scripts/_memory.py` and `scripts/memory_write.py`, and the scope rules from `scripts/_gen_util.py`. The parity tests run those scripts and compare, so a change to either side that is not made on both fails the suite.
