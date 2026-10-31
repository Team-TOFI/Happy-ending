import {
  normalizeProfile,
  normalizeSelection,
  normalizeWardrobe,
} from "./domain.ts";
export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}
export function createStorage(
  storage: StorageLike | null,
  onError: () => void = () => {},
) {
  let failed = false;
  const report = () => {
    if (!failed) {
      failed = true;
      onError();
    }
  };
  function read(key: string, fallback: unknown): unknown {
    try {
      const value = storage?.getItem(`tofi.v1.${key}`);
      if (!storage) report();
      return value ? JSON.parse(value) : fallback;
    } catch {
      report();
      return fallback;
    }
  }
  function write(key: string, value: unknown): boolean {
    try {
      if (!storage) throw new Error("Unavailable");
      storage.setItem(`tofi.v1.${key}`, JSON.stringify(value));
      return true;
    } catch {
      report();
      return false;
    }
  }
  return {
    profile: () => normalizeProfile(read("profile", {})),
    wardrobe: () => normalizeWardrobe(read("wardrobe", [])),
    selection: () => normalizeSelection(read("selection", null)),
    write,
  };
}
