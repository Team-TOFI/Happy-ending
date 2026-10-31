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
test("restored state retains recommendation context but never loads an unowned local wardrobe", async () => {
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
  assert.equal(restored.wardrobe.length, 0);
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

test("member wardrobes clear immediately on account switch and cannot be changed by guests", async () => {
  const { getCatalog } = await import("../src/lib/tofi/catalog.ts");
  const product = { ...getCatalog()[0], id: "musinsa:1", sample: false };
  let owner = "A";
  const data = new Map<
    string,
    import("../src/lib/tofi/types.ts").SavedItem[]
  >();
  let release: (() => void) | undefined;
  let delay = false;
  const account: import("../src/lib/tofi/account.ts").AccountService = {
    async me() {
      const id = owner;
      if (delay)
        await new Promise<void>((resolve) => {
          release = resolve;
        });
      return { id, name: id, email: id + "@example.test" };
    },
    async list() {
      return data.get(owner) || [];
    },
    async save(_id, profile, comment) {
      const item = {
        product,
        profile,
        comment,
        savedAt: new Date().toISOString(),
      };
      data.set(owner, [item]);
      return item;
    },
    async remove() {
      data.set(owner, []);
    },
  };
  const store = createTofiStore({
    local: memory(),
    session: memory(),
    account,
  });
  assert.equal(await store.save(product, profile, "비회원"), false);
  await store.syncAccount("A");
  assert.equal(await store.save(product, profile, "A의 상품"), true);
  assert.equal(store.getSnapshot().wardrobe.length, 1);
  owner = "B";
  delay = true;
  const changing = store.syncAccount("B");
  assert.equal(store.getSnapshot().member, null);
  assert.deepEqual(store.getSnapshot().wardrobe, []);
  release?.();
  await changing;
  delay = false;
  assert.equal(store.getSnapshot().member?.id, "B");
  assert.equal(store.getSnapshot().wardrobe.length, 0);
  await store.syncAccount(null);
  assert.equal(store.getSnapshot().member, null);
  assert.equal(store.getSnapshot().wardrobe.length, 0);
  assert.equal(data.get("A")?.length, 1);
});

test("a previous member's slow response cannot repopulate the new account", async () => {
  let release!: (value: import("../src/lib/tofi/account.ts").Member) => void;
  const account: import("../src/lib/tofi/account.ts").AccountService = {
    me: () =>
      new Promise((resolve) => {
        release = resolve;
      }),
    async list() {
      return [];
    },
    async save() {
      throw new Error("unused");
    },
    async remove() {},
  };
  const store = createTofiStore({
    local: memory(),
    session: memory(),
    account,
  });
  const pending = store.syncAccount("A");
  await store.syncAccount(null);
  release({ id: "A", email: "a@example.test", name: "A" });
  await pending;
  assert.equal(store.getSnapshot().member, null);
  assert.equal(store.getSnapshot().accountStatus, "guest");
});

test("same-member refresh does not strand an in-flight wardrobe save", async () => {
  const { getCatalog } = await import("../src/lib/tofi/catalog.ts");
  const product = { ...getCatalog()[0], id: "musinsa:1", sample: false };
  let finish!: (item: import("../src/lib/tofi/types.ts").SavedItem) => void;
  const account: import("../src/lib/tofi/account.ts").AccountService = {
    async me() {
      return { id: "A", name: "A", email: "a@example.test" };
    },
    async list() {
      return [];
    },
    save: () =>
      new Promise((resolve) => {
        finish = resolve;
      }),
    async remove() {},
  };
  const store = createTofiStore({
    local: memory(),
    session: memory(),
    account,
  });
  await store.syncAccount("A");
  const saving = store.save(product, profile, "A의 상품");
  await store.syncAccount("A");
  finish({
    product,
    profile,
    comment: "A의 상품",
    savedAt: new Date().toISOString(),
  });
  assert.equal(await saving, true);
  assert.equal(store.getSnapshot().wardrobePending, false);
  assert.equal(store.getSnapshot().wardrobe.length, 1);
});

test("legacy anonymous saved items are never assigned to a new member", async () => {
  const { getCatalog } = await import("../src/lib/tofi/catalog.ts");
  const local = memory();
  local.setItem(
    "tofi.v1.wardrobe",
    JSON.stringify([
      {
        product: getCatalog()[0],
        profile,
        comment: "알 수 없는 이전 사용자",
        savedAt: new Date().toISOString(),
      },
    ]),
  );
  const account: import("../src/lib/tofi/account.ts").AccountService = {
    async me() {
      return { id: "new-user", email: "new@example.test", name: "새 회원" };
    },
    async list() {
      return [];
    },
    async save() {
      throw new Error("unused");
    },
    async remove() {},
  };
  const store = createTofiStore({ local, session: memory(), account });
  assert.equal(store.getSnapshot().wardrobe.length, 0);
  await store.syncAccount("new-user");
  assert.equal(store.getSnapshot().wardrobe.length, 0);
});
