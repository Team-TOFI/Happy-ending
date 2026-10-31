import test from "node:test";
import assert from "node:assert/strict";
import { safeReturnPath } from "../src/lib/supabase/redirect.ts";
import { createAccountService, AccountError } from "../src/lib/tofi/account.ts";

test("OAuth return paths never redirect to external URLs or repeat login", () => {
  for (const value of [
    "https://evil.test",
    "//evil.test",
    "/\\evil.test",
    "/login",
    "/auth/callback",
  ])
    assert.equal(safeReturnPath(value), "/wardrobe");
  assert.equal(safeReturnPath("/picks/outfit-1"), "/picks/outfit-1");
});

test("member API uses the access token and never sends a client owner ID", async () => {
  const calls: { url: string; init: RequestInit }[] = [];
  const service = createAccountService(
    async () => "verified-token",
    async (url, init) => {
      calls.push({ url: String(url), init: init || {} });
      return new Response(
        JSON.stringify({ id: "A", email: "a@example.test", name: "A" }),
        { status: 200 },
      );
    },
    "https://api.gomin.today/",
  );
  assert.equal((await service.me()).id, "A");
  assert.equal(calls[0].url, "https://api.gomin.today/auth/me");
  assert.equal(
    (calls[0].init.headers as Record<string, string>).Authorization,
    "Bearer verified-token",
  );
  assert.equal(calls[0].init.cache, "no-store");
  const guest = createAccountService(async () => null);
  await assert.rejects(
    guest.me(),
    (error) => error instanceof AccountError && error.status === 401,
  );
});

test("wardrobe requests go directly to the configured backend", async () => {
  const calls: { url: string; init: RequestInit }[] = [];
  const service = createAccountService(
    async () => "verified-token",
    async (url, init) => {
      calls.push({ url: String(url), init: init || {} });
      return init?.method === "DELETE"
        ? new Response(null, { status: 204 })
        : Response.json({ items: [] });
    },
    "https://api.gomin.today/",
  );
  assert.deepEqual(await service.list(), []);
  await service.remove("musinsa:1");
  assert.deepEqual(calls.map((c) => c.url), [
    "https://api.gomin.today/wardrobe",
    "https://api.gomin.today/wardrobe/musinsa%3A1",
  ]);
  assert.equal(calls[1].init.method, "DELETE");
  assert.equal((calls[1].init.headers as Record<string, string>).Authorization, "Bearer verified-token");
});
