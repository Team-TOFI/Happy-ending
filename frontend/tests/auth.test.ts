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
  );
  assert.equal((await service.me()).id, "A");
  assert.equal(calls[0].url, "/api/auth/me");
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
