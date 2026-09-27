import type { OAuthHelpers } from "@cloudflare/workers-oauth-provider";

export interface Env {
  OAUTH_KV: KVNamespace;
  OAUTH_PROVIDER: OAuthHelpers;
  GITHUB_CLIENT_ID: string;
  GITHUB_CLIENT_SECRET: string;
  GITHUB_TOKEN: string;
  GITHUB_REPO: string;
  GITHUB_BRANCH: string;
  ALLOWED_GITHUB_LOGINS: string;
  ALLOWED_REDIRECT_HOSTS: string;
  TIMEZONE: string;
  PUBLIC_URL: string;
}

export const PRODUCER = "augment/connector";

export function list(v: string | undefined): string[] {
  return (v || "").split(",").map((s) => s.trim().toLowerCase()).filter(Boolean);
}

/** `YYYY-MM-DD HH:MM` in the vault's clock, the form `updated:` carries. */
export function stamp(timeZone: string, now = new Date()): string {
  return new Intl.DateTimeFormat("sv-SE", {
    timeZone: timeZone || "UTC",
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(now).replace("T", " ");
}
