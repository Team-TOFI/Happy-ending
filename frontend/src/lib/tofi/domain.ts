import { BODY_TYPES, OCCASIONS, MOODS, TAGS, CATEGORIES } from "./catalog.ts";
import { record } from "./types.ts";
import type {
  BodyType,
  Category,
  Outfit,
  Product,
  Profile,
  SavedItem,
  Selection,
} from "./types.ts";

function bodyType(value: unknown): BodyType | "" {
  return BODY_TYPES.find((type) => type === value) || "";
}

export function normalizeProfile(value: unknown = {}): Profile {
  const p = record(value);
  const mode = p.mode === "mix" ? "mix" : "single";
  const upper = bodyType(p.upper);
  return {
    mode,
    upper,
    lower: mode === "single" ? upper : bodyType(p.lower),
    group: p.group === "남성" ? "남성" : "여성",
    occasion: OCCASIONS.find(([name]) => name === p.occasion)?.[0] || "",
    mood: MOODS.find(({ name }) => name === p.mood)?.name || "",
    tags: Array.isArray(p.tags)
      ? [
          ...new Set(
            p.tags.filter(
              (tag): tag is string =>
                typeof tag === "string" && TAGS.includes(tag),
            ),
          ),
        ].slice(0, 3)
      : [],
  };
}
export function bodyComplete(p: Profile): boolean {
  return !!p.upper && !!p.lower;
}
export function profileComplete(p: Profile): boolean {
  return bodyComplete(p) && !!p.occasion && !!p.mood;
}
export function chooseType(
  profile: Profile,
  part: "upper" | "lower",
  type: BodyType,
): Profile {
  return normalizeProfile({
    ...profile,
    [part]: type,
    ...(profile.mode === "single" ? { upper: type, lower: type } : {}),
  });
}
export function toggleTag(tags: string[], tag: string): string[] {
  if (!TAGS.includes(tag)) return tags;
  if (tags.includes(tag)) return tags.filter((item) => item !== tag);
  return tags.length < 3 ? [...tags, tag] : tags;
}
export function profileText(p: Profile): string {
  return `상체 ${p.upper || "미선택"} · 하체 ${p.lower || "미선택"}`;
}
export function safeUrl(value: unknown): string | null {
  if (typeof value !== "string" || value.length > 3000) return null;
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) &&
      !url.username &&
      !url.password
      ? url.href
      : null;
  } catch {
    return null;
  }
}
export function normalizeProduct(value: unknown): Product | null {
  const p = record(value);
  if (
    typeof p.id !== "string" ||
    !p.id ||
    p.id.length > 100 ||
    typeof p.name !== "string" ||
    !p.name.trim() ||
    p.name.length > 160 ||
    !CATEGORIES.slice(1).some((c) => c === p.category) ||
    typeof p.price !== "number" ||
    !Number.isFinite(p.price) ||
    p.price < 0 ||
    p.price > 1e9
  )
    return null;
  const sample = p.sample === true;
  const sprite =
    sample &&
    typeof p.sprite === "number" &&
    Number.isInteger(p.sprite) &&
    p.sprite >= 0 &&
    p.sprite < 12
      ? p.sprite
      : null;
  return {
    id: p.id,
    name: p.name,
    category: p.category as Category,
    price: Math.round(p.price),
    sprite,
    sample,
    ...(p.garmentType === "PANTS" || p.garmentType === "SKIRT"
      ? { garmentType: p.garmentType }
      : {}),
    imageUrl: safeUrl(p.imageUrl),
    url: sample ? null : safeUrl(p.url),
  };
}
export function normalizeRecommendations(value: unknown): Outfit[] {
  const data = record(value);
  if (!Array.isArray(data.outfits))
    throw new Error("추천 응답 형식을 확인할 수 없어요. 다시 시도해주세요.");
  const used = new Set<string>();
  return data.outfits.slice(0, 3).map((value, index) => {
    const o = record(value);
    if (
      typeof o.name !== "string" ||
      !o.name.trim() ||
      o.name.length > 100 ||
      typeof o.comment !== "string" ||
      o.comment.length > 1000 ||
      !Array.isArray(o.products)
    )
      throw new Error("코디 정보를 불러오지 못했어요. 다시 시도해주세요.");
    const products = o.products.slice(0, 4).map(normalizeProduct);
    if (
      !products.length ||
      products.some((p) => !p) ||
      new Set(products.map((p) => p?.id)).size !== products.length
    )
      throw new Error("상품 정보가 올바르지 않아요. 다시 시도해주세요.");
    const id =
      typeof o.id === "string" && o.id && o.id.length <= 100
        ? o.id
        : String(index + 1);
    if (used.has(id))
      throw new Error("코디 정보가 중복되었어요. 다시 시도해주세요.");
    used.add(id);
    return {
      id,
      name: o.name,
      comment: o.comment,
      products: products as Product[],
      revision: typeof o.revision === "string" ? o.revision.slice(0, 300) : "",
    };
  });
}
export function normalizeWardrobe(value: unknown): SavedItem[] {
  if (!Array.isArray(value)) return [];
  const ids = new Set<string>();
  return value.slice(0, 500).flatMap((value) => {
    const entry = record(value);
    const product = normalizeProduct(entry.product);
    if (!product || ids.has(product.id)) return [];
    ids.add(product.id);
    return [
      {
        product,
        profile: normalizeProfile(entry.profile),
        comment:
          typeof entry.comment === "string" ? entry.comment.slice(0, 1000) : "",
        savedAt:
          typeof entry.savedAt === "string" &&
          Number.isFinite(Date.parse(entry.savedAt))
            ? entry.savedAt
            : new Date(0).toISOString(),
      },
    ];
  });
}
export function normalizeSelection(value: unknown): Selection {
  const data = record(value);
  const profile = normalizeProfile(data.profile);
  if (!profileComplete(profile))
    return { outfits: [], profile: null, requested: false };
  try {
    return {
      outfits: normalizeRecommendations(data),
      profile,
      requested: data.requested === true,
    };
  } catch {
    return { outfits: [], profile: null, requested: false };
  }
}
export function toggleSaved(
  wardrobe: SavedItem[],
  product: Product,
  profile: Profile,
  comment: string,
  now = new Date(),
): SavedItem[] {
  return wardrobe.some((entry) => entry.product.id === product.id)
    ? wardrobe.filter((entry) => entry.product.id !== product.id)
    : [
        {
          product: { ...product },
          profile: structuredClone(profile),
          comment,
          savedAt: now.toISOString(),
        },
        ...wardrobe,
      ];
}
