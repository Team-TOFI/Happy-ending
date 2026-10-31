import { freshProfile } from "./catalog.ts";
import { createRecommendationService } from "./api.ts";
import { normalizeProfile, toggleSaved } from "./domain.ts";
import { createStorage } from "./storage.ts";
import type { StorageLike } from "./storage.ts";
import type { Product, Profile, SavedItem, Selection } from "./types.ts";

export interface TofiState extends Omit<Selection, "profile"> {
  profile: Profile;
  resultProfile: Profile | null;
  wardrobe: SavedItem[];
  ready: boolean;
  storageUnavailable: boolean;
  pending: { target: string; kind: "recommend" | "refine" } | null;
  error: string;
  errorTarget: string | null;
  toast: string;
}

export const serverSnapshot: TofiState = {
  profile: freshProfile(),
  resultProfile: null,
  outfits: [],
  wardrobe: [],
  requested: false,
  ready: false,
  storageUnavailable: false,
  pending: null,
  error: "",
  errorTarget: null,
  toast: "",
};

interface StoreOptions {
  local: StorageLike | null;
  session: StorageLike | null;
  service?: ReturnType<typeof createRecommendationService>;
}

export function createTofiStore({
  local,
  session,
  service = createRecommendationService(),
}: StoreOptions) {
  let storageUnavailable = false;
  const storage = createStorage(local, () => {
    storageUnavailable = true;
  });
  const cache = createStorage(session);
  const profile = storage.profile();
  const wardrobe = storage.wardrobe();
  const selection = cache.selection();
  let state: TofiState = {
    ...serverSnapshot,
    profile,
    wardrobe,
    outfits: selection.outfits,
    resultProfile: selection.profile,
    requested: selection.requested,
    ready: true,
    storageUnavailable,
  };
  const listeners = new Set<() => void>();
  let controller: AbortController | null = null;
  let version = 0;
  let toastTimer: ReturnType<typeof setTimeout> | undefined;

  function publish(patch: Partial<TofiState>) {
    state = { ...state, ...patch, storageUnavailable };
    listeners.forEach((listener) => listener());
  }
  function saveSelection() {
    cache.write("selection", {
      outfits: state.outfits,
      profile: state.resultProfile,
      requested: state.requested,
    });
  }
  function notice(message: string) {
    clearTimeout(toastTimer);
    publish({ toast: message });
    toastTimer = setTimeout(() => publish({ toast: "" }), 3500);
  }
  function cancelRequest() {
    controller?.abort();
    controller = null;
    version += 1;
  }
  function updateProfile(next: Profile) {
    const profile = normalizeProfile(next);
    storage.write("profile", profile);
    publish({ profile });
  }

  async function recommend(profile = state.profile, scenario = "") {
    cancelRequest();
    const requestVersion = ++version;
    const snapshot = structuredClone(profile);
    controller = new AbortController();
    publish({
      pending: { target: "/picks", kind: "recommend" },
      outfits: [],
      resultProfile: snapshot,
      requested: true,
      error: "",
      errorTarget: "/picks",
    });
    try {
      const outfits = await service.request(snapshot, {
        signal: controller.signal,
        scenario,
      });
      if (requestVersion !== version) return;
      publish({ outfits });
      saveSelection();
    } catch (error) {
      if (
        requestVersion !== version ||
        (error instanceof Error && error.name === "AbortError")
      )
        return;
      publish({
        error:
          error instanceof Error
            ? error.message
            : "추천을 가져오지 못했어요. 다시 시도해주세요.",
      });
    } finally {
      if (requestVersion === version) {
        controller = null;
        publish({ pending: null });
      }
    }
  }
  async function refine(outfitId: string, refinement: string) {
    const previous = state.outfits.find((o) => o.id === outfitId);
    if (
      !previous ||
      !state.resultProfile ||
      !refinement.trim() ||
      state.pending
    )
      return false;
    cancelRequest();
    const requestVersion = ++version;
    const snapshot = structuredClone(state.resultProfile);
    controller = new AbortController();
    publish({
      pending: {
        target: `/picks/${encodeURIComponent(outfitId)}`,
        kind: "refine",
      },
      error: "",
      errorTarget: `/picks/${encodeURIComponent(outfitId)}`,
    });
    try {
      const revised = await service.request(snapshot, {
        refinement: refinement.trim().slice(0, 300),
        previous,
        signal: controller.signal,
      });
      if (requestVersion !== version) return false;
      if (!revised.length)
        throw new Error(
          "요청에 맞는 대안을 찾지 못했어요. 기존 코디를 유지했어요. 다른 요청을 골라주세요.",
        );
      publish({
        outfits: state.outfits.map((o) =>
          o.id === outfitId
            ? { ...revised[0], id: outfitId, revision: refinement }
            : o,
        ),
      });
      saveSelection();
      notice("선택한 조건을 유지하고 코디를 조정했어요.");
      return true;
    } catch (error) {
      if (
        requestVersion === version &&
        !(error instanceof Error && error.name === "AbortError")
      )
        publish({
          error:
            error instanceof Error
              ? error.message
              : "수정을 완료하지 못했어요. 다시 시도해주세요.",
        });
      return false;
    } finally {
      if (requestVersion === version) {
        controller = null;
        publish({ pending: null });
      }
    }
  }
  return {
    getSnapshot: () => state,
    subscribe(listener: () => void) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    updateProfile,
    recommend,
    refine,
    save(product: Product, profile: Profile, comment: string) {
      const saved = state.wardrobe.some(
        (item) => item.product.id === product.id,
      );
      const wardrobe = toggleSaved(state.wardrobe, product, profile, comment);
      storage.write("wardrobe", wardrobe);
      publish({ wardrobe });
      notice(saved ? "옷장에서 꺼냈어요." : "내 옷장에 담았어요.");
    },
    cancelOutside(pathname: string) {
      if (state.pending && state.pending.target !== pathname) {
        const cancelledRecommendation = state.pending.kind === "recommend";
        cancelRequest();
        publish({
          pending: null,
          error: "",
          errorTarget: null,
          ...(cancelledRecommendation ? { requested: false } : {}),
        });
      } else if (state.error && state.errorTarget !== pathname) {
        publish({ error: "", errorTarget: null });
      }
    },
    syncStorage() {
      publish({ profile: storage.profile(), wardrobe: storage.wardrobe() });
    },
    clearError() {
      if (state.error) publish({ error: "", errorTarget: null });
    },
  };
}

export const recommendationService = createRecommendationService({
  apiBaseUrl: process.env.NEXT_PUBLIC_RECOMMENDATION_API_BASE_URL,
});
let browserStore: ReturnType<typeof createTofiStore> | undefined;
function getBrowserStore() {
  if (typeof window === "undefined") return undefined;
  if (!browserStore) {
    let local: StorageLike | null = null;
    let session: StorageLike | null = null;
    try {
      local = window.localStorage;
    } catch {
      /* Storage fallback is surfaced in the shell. */
    }
    try {
      session = window.sessionStorage;
    } catch {
      /* Selection caching is optional. */
    }
    browserStore = createTofiStore({
      local,
      session,
      service: recommendationService,
    });
    window.addEventListener("storage", (event) => {
      if (event.key === null || event.key.startsWith("tofi.v1."))
        browserStore?.syncStorage();
    });
  }
  return browserStore;
}
export const getSnapshot = () =>
  getBrowserStore()?.getSnapshot() || serverSnapshot;
export const getServerSnapshot = () => serverSnapshot;
export const subscribe = (listener: () => void) =>
  getBrowserStore()?.subscribe(listener) || (() => {});
export const actions = {
  updateProfile: (profile: Profile) =>
    getBrowserStore()?.updateProfile(profile),
  recommend: (profile?: Profile, scenario?: string) =>
    getBrowserStore()?.recommend(profile, scenario),
  refine: (id: string, request: string) =>
    getBrowserStore()?.refine(id, request),
  save: (product: Product, profile: Profile, comment: string) =>
    getBrowserStore()?.save(product, profile, comment),
  cancelOutside: (path: string) => getBrowserStore()?.cancelOutside(path),
  clearError: () => getBrowserStore()?.clearError(),
};
