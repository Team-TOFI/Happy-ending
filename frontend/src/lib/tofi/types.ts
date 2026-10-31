export type BodyType = "웨이브" | "스트레이트" | "내추럴";
export type ProductGroup = "여성" | "남성";
export type Mood = "미니멀" | "로맨틱" | "캐주얼" | "시크";
export type Category = "상의" | "하의" | "아우터" | "신발" | "가방·액세서리";
export type Filter = "전체" | Category;

export interface Profile {
  mode: "single" | "mix";
  upper: BodyType | "";
  lower: BodyType | "";
  group: ProductGroup;
  occasion: string;
  mood: Mood | "";
  tags: string[];
}

export interface Product {
  id: string;
  name: string;
  category: Category;
  price: number;
  sprite: number | null;
  imageUrl: string | null;
  url: string | null;
  sample: boolean;
  garmentType?: "PANTS" | "SKIRT" | null;
}

export interface Outfit {
  id: string;
  name: string;
  comment: string;
  products: Product[];
  revision?: string;
}

export interface SavedItem {
  product: Product;
  profile: Profile;
  comment: string;
  savedAt: string;
}

export interface Selection {
  outfits: Outfit[];
  profile: Profile | null;
  requested: boolean;
}

export interface RecommendationOptions {
  refinement?: string;
  previous?: Outfit | null;
  signal?: AbortSignal;
  scenario?: string;
}

export interface ServiceConfig {
  apiBaseUrl?: string;
  timeoutMs?: number;
  demoDelayMs?: number;
}

export function record(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}
