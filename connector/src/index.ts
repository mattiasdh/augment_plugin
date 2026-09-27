/**
 * augment connector: a remote MCP server over an augment vault on GitHub, for the
 * surfaces that run neither a shell nor a local MCP server (claude.ai on the web,
 * the mobile apps) and for Desktop when the Obsidian tier is not running.
 *
 * Who may connect: OAuth 2.1 with dynamic client registration, handled by
 * @cloudflare/workers-oauth-provider, with GitHub as the sign-in. Two gates stand
 * in front of a token being issued. The OAuth client's redirect must go to one of
 * ALLOWED_REDIRECT_HOSTS (Claude's own callback hosts by default), so a token can
 * only ever land in a Claude account; and the person signing in at GitHub must be
 * one of ALLOWED_GITHUB_LOGINS. The GitHub sign-in asks for no scope: it proves
 * identity and nothing else. Reading and writing the vault uses a separate
 * fine-grained token, GITHUB_TOKEN, limited to the one repository.
 */
import OAuthProvider, { type AuthRequest } from "@cloudflare/workers-oauth-provider";
import { type Env, PRODUCER, list, stamp } from "./env";
import { GitHubRepo } from "./github";
import { serve, VERSION } from "./mcp";

const STATE_TTL = 600;

function page(status: number, title: string, text: string): Response {
  const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]!));
  return new Response(`<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>${esc(title)}</title>` +
    `<body style="font:16px/1.5 system-ui;max-width:36rem;margin:3rem auto;padding:0 1rem"><h1 style="font-size:1.25rem">${esc(title)}</h1><p>${esc(text)}</p>`,
    { status, headers: { "Content-Type": "text/html; charset=utf-8" } });
}

function randomToken(): string {
  const b = crypto.getRandomValues(new Uint8Array(24));
  return btoa(String.fromCharCode(...b)).replace(/[+/=]/g, (c) => ({ "+": "-", "/": "_", "=": "" }[c]!));
}

async function authorize(request: Request, env: Env): Promise<Response> {
  let oauthReq: AuthRequest;
  try {
    oauthReq = await env.OAUTH_PROVIDER.parseAuthRequest(request);
  } catch (e) {
    return page(400, "Invalid authorization request", (e as Error).message);
  }
  let host = "";
  try { host = new URL(oauthReq.redirectUri).hostname.toLowerCase(); } catch { /* refused below */ }
  if (!list(env.ALLOWED_REDIRECT_HOSTS).includes(host)) {
    return page(400, "Client not allowed", `This connector only issues tokens to Claude. The client asked to return to ${host || "an invalid address"}.`);
  }
  const state = randomToken();
  await env.OAUTH_KV.put(`github-state:${state}`, JSON.stringify(oauthReq), { expirationTtl: STATE_TTL });
  const gh = new URL("https://github.com/login/oauth/authorize");
  gh.searchParams.set("client_id", env.GITHUB_CLIENT_ID);
  gh.searchParams.set("redirect_uri", new URL("/callback", request.url).href);
  gh.searchParams.set("state", state);
  gh.searchParams.set("allow_signup", "false");
  return Response.redirect(gh.href, 302);
}

async function callback(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const state = url.searchParams.get("state") ?? "";
  const code = url.searchParams.get("code") ?? "";
  const stored = state ? await env.OAUTH_KV.get(`github-state:${state}`) : null;
  if (!stored || !code) return page(400, "Sign-in expired", "Start the connection again from Claude.");
  await env.OAUTH_KV.delete(`github-state:${state}`);
  const oauthReq = JSON.parse(stored) as AuthRequest;

  const tokenRes = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json", "User-Agent": "augment-connector" },
    body: JSON.stringify({ client_id: env.GITHUB_CLIENT_ID, client_secret: env.GITHUB_CLIENT_SECRET, code, redirect_uri: new URL("/callback", request.url).href }),
  });
  const tok = (await tokenRes.json()) as { access_token?: string; error_description?: string };
  if (!tok.access_token) return page(502, "GitHub sign-in failed", tok.error_description ?? "No token returned.");
  const userRes = await fetch("https://api.github.com/user", {
    headers: { Authorization: `Bearer ${tok.access_token}`, Accept: "application/vnd.github+json", "User-Agent": "augment-connector" },
  });
  const user = (await userRes.json()) as { login?: string; id?: number };
  // The identity token has done its job; revoking it is best effort.
  const basic = btoa(`${env.GITHUB_CLIENT_ID}:${env.GITHUB_CLIENT_SECRET}`);
  await fetch(`https://api.github.com/applications/${env.GITHUB_CLIENT_ID}/token`, {
    method: "DELETE",
    headers: { Authorization: `Basic ${basic}`, Accept: "application/vnd.github+json", "User-Agent": "augment-connector", "Content-Type": "application/json" },
    body: JSON.stringify({ access_token: tok.access_token }),
  }).catch(() => undefined);

  const login = (user.login ?? "").toLowerCase();
  if (!login || !list(env.ALLOWED_GITHUB_LOGINS).includes(login)) {
    return page(403, "Not allowed", `GitHub account ${user.login ?? "(unknown)"} may not use this connector.`);
  }
  const { redirectTo } = await env.OAUTH_PROVIDER.completeAuthorization({
    request: oauthReq,
    userId: String(user.id),
    metadata: { label: login },
    scope: oauthReq.scope,
    props: { login },
  });
  return Response.redirect(redirectTo, 302);
}

const defaultHandler = {
  async fetch(request: Request, env: Env): Promise<Response> {
    const { pathname } = new URL(request.url);
    if (pathname === "/authorize") return authorize(request, env);
    if (pathname === "/callback") return callback(request, env);
    if (pathname === "/") return page(200, "augment connector", `A remote MCP server for an augment vault, version ${VERSION}. Add ${new URL("/mcp", request.url).href} as a custom connector in Claude.`);
    return page(404, "Not found", "Nothing here.");
  },
};

const apiHandler = {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const login = String((ctx as ExecutionContext & { props?: { login?: string } }).props?.login ?? "").toLowerCase();
    // Checked on every call as well as at sign-in, so removing a login locks it out at once.
    if (!list(env.ALLOWED_GITHUB_LOGINS).includes(login)) return new Response("forbidden", { status: 403 });
    const repo = new GitHubRepo(env.GITHUB_TOKEN, env.GITHUB_REPO, env.GITHUB_BRANCH || "main");
    return serve(request, { repo, now: () => stamp(env.TIMEZONE), by: PRODUCER });
  },
};

// The OAuth metadata names the server's own public URL, which exists only once the
// Worker is deployed, so the provider is built on the first request from PUBLIC_URL.
let provider: OAuthProvider<Env> | null = null;

function build(env: Env): OAuthProvider<Env> {
  const origin = String(env.PUBLIC_URL || "").replace(/\/+$/, "");
  if (!/^https:\/\/[a-z0-9.-]+$/.test(origin) && !/^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(origin)) {
    throw new Error(`PUBLIC_URL must be the Worker's https origin, not ${env.PUBLIC_URL}`);
  }
  return new OAuthProvider<Env>({
    apiRoute: "/mcp",
    apiHandler,
    defaultHandler,
    authorizeEndpoint: "/authorize",
    tokenEndpoint: "/token",
    clientRegistrationEndpoint: "/register",
    clientIdMetadataDocumentEnabled: true,
    scopesSupported: ["vault"],
    resourceMetadata: {
      resource: `${origin}/mcp`,
      authorization_servers: [origin],
      scopes_supported: ["vault"],
      bearer_methods_supported: ["header"],
      resource_name: "augment vault",
    },
    accessTokenTTL: 3600,
    refreshTokenTTL: 30 * 24 * 3600,
  });
}

export default {
  fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    provider ??= build(env);
    return provider.fetch(request, env, ctx);
  },
} satisfies ExportedHandler<Env>;
