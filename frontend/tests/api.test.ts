import test from "node:test";
import assert from "node:assert/strict";
import {
  createRecommendationService,
  demoRecommendations,
} from "../src/lib/tofi/api.ts";
import type { Profile } from "../src/lib/tofi/types.ts";
const profile: Profile = {
  mode: "mix",
  upper: "웨이브",
  lower: "스트레이트",
  group: "여성",
  occasion: "발표",
  mood: "미니멀",
  tags: ["차분한 색감", "편한 착용감"],
};

test("demo produces three outfits of four products and respects group and mood", async () => {
  const service = createRecommendationService({ demoDelayMs: 0 });
  const outfits = await service.request(profile);
  assert.equal(service.sample, true);
  assert.equal(outfits.length, 3);
  assert.ok(outfits.every((o) => o.products.length === 4));
  const male = await service.request({
    ...profile,
    group: "남성",
    mood: "캐주얼",
  });
  assert.ok(male.every((o) => o.products.every((p) => p.id.startsWith("m-"))));
  assert.equal(male[0].products[0].name, "토프 니트 카디건");
});
test("refinement changes relevant items and comments without mutating previous outfit", async () => {
  const service = createRecommendationService({ demoDelayMs: 0 });
  const [original] = await service.request(profile);
  const snapshot = structuredClone(original);
  const [skirt] = await service.request(profile, {
    previous: original,
    refinement: "스커트로 바꾸기",
  });
  assert.ok(skirt.products[1].id.endsWith("-skirt"));
  assert.equal(skirt.products[0].id, original.products[0].id);
  assert.notEqual(skirt.comment, original.comment);
  assert.deepEqual(original, snapshot);
  const [budget] = await service.request(profile, {
    previous: original,
    refinement: "예산 낮추기",
  });
  assert.ok(
    budget.products.reduce((s, p) => s + p.price, 0) <
      original.products.reduce((s, p) => s + p.price, 0),
  );
  await assert.rejects(
    service.request(profile, { previous: budget, refinement: "예산 낮추기" }),
    /더 낮은 가격/,
  );
  await assert.rejects(
    service.request(profile, {
      previous: original,
      refinement: "완전히 새로운 요청",
    }),
    /샘플 모드/,
  );
});
test("demo comments describe the products after mood-specific ordering", () => {
  assert.match(
    demoRecommendations({ ...profile, mood: "캐주얼" }).outfits[0].comment,
    /카디건/,
  );
  assert.match(
    demoRecommendations({ ...profile, mood: "로맨틱" }).outfits[0].comment,
    /블루/,
  );
});
test("API posts original profile and refinement, validates response and handles HTTP failure", async () => {
  const requests: { url: string; options?: RequestInit }[] = [];
  const service = createRecommendationService(
    { apiBaseUrl: "https://api.example.test/" },
    async (url, options) => {
      requests.push({ url: String(url), options });
      return new Response(JSON.stringify(demoRecommendations(profile)), {
        status: 200,
      });
    },
  );
  assert.equal(service.sample, false);
  assert.equal(
    (await service.request(profile, { refinement: "캐주얼하게" })).length,
    3,
  );
  assert.equal(requests[0].url, "https://api.example.test/recommendations");
  assert.deepEqual(
    JSON.parse(String(requests[0].options?.body)).profile,
    profile,
  );
  assert.equal(
    JSON.parse(String(requests[0].options?.body)).refinement,
    "캐주얼하게",
  );
  const failing = createRecommendationService(
    { apiBaseUrl: "https://api.example.test" },
    async () => new Response("", { status: 503 }),
  );
  await assert.rejects(failing.request(profile), /다시 시도/);
  const malformed = createRecommendationService(
    { apiBaseUrl: "https://api.example.test" },
    async () => new Response("{}"),
  );
  await assert.rejects(malformed.request(profile), /응답 형식/);
});
test("empty, failed, retry and aborted recommendations are recoverable", async () => {
  const service = createRecommendationService({ demoDelayMs: 0 });
  assert.deepEqual(await service.request(profile, { scenario: "empty" }), []);
  await assert.rejects(
    service.request(profile, { scenario: "error" }),
    /다시 시도/,
  );
  assert.equal((await service.request(profile)).length, 3);
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(
    service.request(profile, { signal: controller.signal }),
    { name: "AbortError" },
  );
  await assert.rejects(service.request({ ...profile, upper: "" }), /먼저 선택/);
});
test("live adapter times out and forwards cancellation", async () => {
  const pending: typeof fetch = (_url, options) =>
    new Promise<Response>((_resolve, reject) => {
      const signal = options?.signal;
      if (signal?.aborted) reject(signal.reason);
      else
        signal?.addEventListener("abort", () => reject(signal.reason), {
          once: true,
        });
    });
  const service = createRecommendationService(
    { apiBaseUrl: "https://api.example.test", timeoutMs: 10 },
    pending,
  );
  await assert.rejects(service.request(profile), /응답이 늦어/);
  const controller = new AbortController();
  const request = service.request(profile, { signal: controller.signal });
  controller.abort();
  await assert.rejects(request, { name: "AbortError" });
});
