import test from "node:test";
import assert from "node:assert/strict";
import {
  normalizeProfile,
  chooseType,
  toggleTag,
  normalizeRecommendations,
  normalizeWardrobe,
  toggleSaved,
  profileComplete,
  safeUrl,
} from "../src/lib/tofi/domain.ts";
import { getCatalog } from "../src/lib/tofi/catalog.ts";
import { createStorage } from "../src/lib/tofi/storage.ts";
import type { Profile } from "../src/lib/tofi/types.ts";

export const profile: Profile = {
  mode: "mix",
  upper: "웨이브",
  lower: "스트레이트",
  group: "여성",
  occasion: "발표",
  mood: "미니멀",
  tags: ["차분한 색감", "편한 착용감"],
};
test("single type applies to both parts; mix supports independent choices", () => {
  const single = chooseType(
    normalizeProfile({ ...profile, mode: "single" }),
    "upper",
    "내추럴",
  );
  assert.equal(single.upper, "내추럴");
  assert.equal(single.lower, "내추럴");
  const mix = chooseType({ ...single, mode: "mix" }, "lower", "웨이브");
  assert.equal(mix.upper, "내추럴");
  assert.equal(mix.lower, "웨이브");
});
test("tags stop at three but can be removed and replaced", () => {
  const tags = toggleTag(profile.tags, "허리선 강조");
  assert.equal(tags.length, 3);
  assert.deepEqual(toggleTag(tags, "화사한 색감"), tags);
  assert.equal(
    toggleTag(toggleTag(tags, "차분한 색감"), "화사한 색감").length,
    3,
  );
  assert.deepEqual(
    normalizeProfile({ tags: ["unknown", "차분한 색감", "차분한 색감"] }).tags,
    ["차분한 색감"],
  );
});
test("wardrobe toggles stable IDs and captures original recommendation context", () => {
  const p = structuredClone(profile);
  const product = getCatalog()[0];
  const saved = toggleSaved(
    [],
    product,
    p,
    "저장 당시 코멘트",
    new Date("2026-10-31T00:00:00Z"),
  );
  p.tags.push("허리선 강조");
  p.occasion = "데이트";
  assert.deepEqual(saved[0].profile.tags, profile.tags);
  assert.equal(saved[0].profile.occasion, "발표");
  assert.equal(toggleSaved(saved, product, p, "").length, 0);
  assert.equal(
    normalizeWardrobe([...saved, ...saved, { product: { id: "broken" } }])
      .length,
    1,
  );
});
test("storage survives a new session and recovers from malformed or blocked data", () => {
  const backing = new Map<string, string>();
  const memory = {
    getItem: (key: string) => backing.get(key) || null,
    setItem: (key: string, value: string) => {
      backing.set(key, value);
    },
  };
  const first = createStorage(memory);
  first.write("profile", profile);
  first.write("wardrobe", toggleSaved([], getCatalog()[0], profile, "메모"));
  assert.deepEqual(createStorage(memory).profile(), profile);
  assert.equal(createStorage(memory).wardrobe().length, 1);
  backing.set("tofi.v1.profile", "{bad json");
  let errors = 0;
  assert.equal(
    profileComplete(createStorage(memory, () => errors++).profile()),
    false,
  );
  assert.equal(errors, 1);
  const blocked = createStorage(
    {
      getItem() {
        throw Error();
      },
      setItem() {
        throw Error();
      },
    },
    () => errors++,
  );
  assert.equal(blocked.wardrobe().length, 0);
  assert.equal(blocked.write("profile", profile), false);
  assert.equal(errors, 2);
});
test("responses reject invalid prices, duplicate IDs and unsafe URLs", () => {
  assert.equal(safeUrl("javascript:alert(1)"), null);
  assert.equal(safeUrl("https://user:pass@example.com"), null);
  const product = {
    ...getCatalog()[0],
    sample: false,
    url: "javascript:alert(1)",
    imageUrl: "data:text/html,unsafe",
  };
  const outfit = {
    id: "1",
    name: "#코디",
    comment: "설명",
    products: [product],
  };
  const [valid] = normalizeRecommendations({ outfits: [outfit] });
  assert.equal(valid.products[0].url, null);
  assert.equal(valid.products[0].imageUrl, null);
  assert.equal(valid.products[0].sprite, null);
  assert.throws(() =>
    normalizeRecommendations({
      outfits: [{ ...outfit, products: [{ ...product, price: -1 }] }],
    }),
  );
  assert.throws(() => normalizeRecommendations({ outfits: [outfit, outfit] }));
  assert.deepEqual(normalizeRecommendations({ outfits: [] }), []);
});
test("JSON null profile and null saved context never prevent startup", () => {
  const entry = {
    product: getCatalog()[0],
    profile: null,
    comment: "이전 메모",
    savedAt: "2026-10-31T00:00:00Z",
  };
  const storage = createStorage({
    getItem: (key) =>
      key.endsWith(".profile") ? "null" : JSON.stringify([entry]),
    setItem() {},
  });
  assert.deepEqual(storage.profile(), normalizeProfile({}));
  assert.equal(profileComplete(storage.profile()), false);
  assert.equal(storage.wardrobe().length, 1);
  assert.deepEqual(storage.wardrobe()[0].profile, normalizeProfile({}));
  assert.equal(storage.wardrobe()[0].comment, "이전 메모");
  for (const input of [null, false, 42, "broken", []])
    assert.deepEqual(normalizeProfile(input), normalizeProfile({}));
});
