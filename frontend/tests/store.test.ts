import test from "node:test";
import assert from "node:assert/strict";
import {
  createTofiStore,
  getSnapshot,
  getServerSnapshot,
} from "../src/lib/tofi/store.ts";
import { createRecommendationService } from "../src/lib/tofi/api.ts";
import type { StorageLike } from "../src/lib/tofi/storage.ts";
import type { Profile } from "../src/lib/tofi/types.ts";
const profile: Profile = {
  mode: "mix",
  upper: "웨이브",
  lower: "스트레이트",
  group: "여성",
  occasion: "발표",
  mood: "미니멀",
  tags: ["차분한 색감"],
};
function memory(): StorageLike {
  const data = new Map<string, string>();
  return {
    getItem: (key) => data.get(key) || null,
    setItem(key, value) {
      data.set(key, value);
    },
  };
}
test("SSR snapshot is stable and browser data never enters the server snapshot", () => {
  assert.equal(getServerSnapshot(), getServerSnapshot());
  assert.equal(getSnapshot(), getServerSnapshot());
  const store = createTofiStore({ local: memory(), session: memory() });
  store.updateProfile(profile);
  assert.equal(getServerSnapshot().profile.upper, "");
  assert.equal(getServerSnapshot().ready, false);
});
test("restored state retains saved products, exact recommendation context and session results", async () => {
  const local = memory();
  const session = memory();
  const service = createRecommendationService({ demoDelayMs: 0 });
  const store = createTofiStore({ local, session, service });
  store.updateProfile(profile);
  await store.recommend();
  const first = store.getSnapshot().outfits[0];
  store.save(first.products[0], profile, first.comment);
  store.updateProfile({ ...profile, occasion: "데이트" });
  await store.refine("1", "스커트로 바꾸기");
  assert.equal(store.getSnapshot().resultProfile?.occasion, "발표");
  assert.equal(store.getSnapshot().profile.occasion, "데이트");
  const restored = createTofiStore({ local, session, service }).getSnapshot();
  assert.equal(restored.wardrobe.length, 1);
  assert.equal(restored.wardrobe[0].profile.occasion, "발표");
  assert.equal(restored.outfits.length, 3);
  assert.ok(restored.outfits[0].products[1].id.endsWith("-skirt"));
});
test("navigation cancels pending requests and stale completions cannot update the next screen", async () => {
  const store = createTofiStore({
    local: memory(),
    session: memory(),
    service: createRecommendationService({ demoDelayMs: 20 }),
  });
  const request = store.recommend(profile);
  assert.equal(store.getSnapshot().pending?.target, "/picks");
  store.cancelOutside("/wardrobe");
  await request;
  assert.equal(store.getSnapshot().pending, null);
  assert.equal(store.getSnapshot().requested, false);
  assert.equal(store.getSnapshot().outfits.length, 0);
  assert.equal(store.getSnapshot().error, "");
  await store.recommend(profile);
  assert.equal(store.getSnapshot().outfits.length, 3);
});
test("fast recommendation errors survive navigation to their result page and clear when leaving", async () => {
  const store = createTofiStore({
    local: memory(),
    session: memory(),
    service: createRecommendationService({ demoDelayMs: 0 }),
  });
  await store.recommend(profile, "error");
  assert.match(store.getSnapshot().error, /다시 시도/);
  store.cancelOutside("/picks");
  assert.match(store.getSnapshot().error, /다시 시도/);
  store.cancelOutside("/style/body-type");
  assert.equal(store.getSnapshot().error, "");
});
