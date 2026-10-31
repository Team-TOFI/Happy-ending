import { getCatalog } from "./catalog.ts";
import { normalizeRecommendations, profileComplete } from "./domain.ts";
import type {
  Mood,
  Outfit,
  Product,
  Profile,
  RecommendationOptions,
  ServiceConfig,
} from "./types.ts";

function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    const abort = () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", abort);
      resolve();
    }, ms);
    if (signal?.aborted) abort();
    else signal?.addEventListener("abort", abort, { once: true });
  });
}

export function demoRecommendations(
  profile: Profile,
  refinement = "",
  previous: Outfit | null = null,
): { outfits: Outfit[] } {
  const catalog = getCatalog(profile.group);
  const product = (suffix: string): Product => {
    const item = catalog.find((p) => p.id.endsWith(`-${suffix}`));
    if (!item) throw new Error("현재 상품군에서 샘플 아이템을 찾지 못했어요.");
    return item;
  };
  const names: Record<Mood, string[]> = {
    미니멀: ["#단정한_미니멀", "#부드러운_포인트", "#편안한_단정함"],
    로맨틱: ["#부드러운_로맨틱", "#담백한_포인트", "#편안한_로맨틱"],
    캐주얼: ["#편안한_캐주얼", "#단정한_캐주얼", "#가벼운_일상"],
    시크: ["#담백한_시크", "#차분한_포인트", "#편안한_시크"],
  };
  let arrangements = [
    ["knit", "navy-pants", "brown-loafers", "shoulder-bag"],
    ["blue-shirt", "sand-pants", "black-loafers", "tote-bag"],
    ["cardigan", "cotton-pants", "sneakers", "shoulder-bag"],
  ];
  if (profile.mood === "캐주얼")
    arrangements = [arrangements[2], arrangements[0], arrangements[1]];
  if (profile.mood === "로맨틱")
    arrangements = [arrangements[1], arrangements[0], arrangements[2]];
  if (profile.mood === "시크")
    arrangements = [arrangements[1], arrangements[2], arrangements[0]];
  const comments: Record<string, string> = {
    knit: `부드러운 니트와 곧게 떨어지는 팬츠를 조합했어요. ${profile.occasion}에 입기 좋은 차분한 셀렉션이에요.`,
    "blue-shirt": `가벼운 블루 톤과 정돈된 팬츠로 포인트를 더했어요. ${profile.occasion}에도 단정한 인상을 유지해요.`,
    cardigan: `여유로운 카디건과 스니커즈로 편안하게 골랐어요. ${profile.occasion} 전후 일상에도 자연스럽게 이어져요.`,
  };
  const outfits = arrangements.map((ids, index) => ({
    id: String(index + 1),
    name: names[profile.mood || "미니멀"][index],
    comment: comments[ids[0]],
    products: ids.map(product),
  }));
  if (!refinement || !previous) return { outfits };
  const revised = structuredClone(previous);
  if (/캐주얼|편안|편하게/.test(refinement)) {
    revised.products[0] = product("cardigan");
    revised.products[2] = product("sneakers");
    revised.name = "#편안한_캐주얼";
    revised.comment =
      "부드러운 카디건과 가벼운 스니커즈로 바꿨어요. 선택한 체형·상황·취향은 유지했어요.";
  } else if (/예산|저렴|가격/.test(refinement)) {
    revised.products = ["knit", "cotton-pants", "sneakers", "tote-bag"].map(
      product,
    );
    if (
      revised.products.reduce((sum, p) => sum + p.price, 0) >=
      previous.products.reduce((sum, p) => sum + p.price, 0)
    )
      throw new Error(
        "현재 샘플 상품에서 더 낮은 가격의 조합을 찾지 못했어요. 기존 코디를 유지했어요.",
      );
    revised.name = "#가볍게_단정하게";
    revised.comment =
      "니트·코튼 팬츠·스니커즈·토트백으로 상품 합계를 낮춘 샘플 조합이에요. 기존 프로필과 상황은 유지했어요.";
  } else if (/스커트|바지|팬츠|하의/.test(refinement)) {
    if (profile.group === "남성" && /스커트/.test(refinement))
      throw new Error(
        "현재 남성 샘플에는 스커트가 없어요. 팬츠 변경이나 다른 빠른 요청을 선택해주세요.",
      );
    const skirt =
      profile.group === "여성" &&
      !previous.products.some((p) => p.id.endsWith("-skirt")) &&
      !/바지|팬츠/.test(refinement);
    revised.products[1] = product(skirt ? "skirt" : "cotton-pants");
    revised.name = skirt ? "#부드러운_스커트" : "#편안한_팬츠";
    revised.comment = `${skirt ? "A라인 스커트" : "코튼 팬츠"}로 하의를 바꿨어요. 나머지 아이템과 선택 조건은 유지했어요.`;
  } else
    throw new Error(
      "샘플 모드에서는 캐주얼하게, 예산 낮추기, 하의 바꾸기를 시연할 수 있어요. 빠른 요청을 골라주세요.",
    );
  revised.revision = refinement;
  return { outfits: [revised] };
}

export function createRecommendationService(
  config: ServiceConfig = {},
  fetcher: typeof fetch = globalThis.fetch,
) {
  const base = (config.apiBaseUrl || "").replace(/\/$/, "");
  const sample = !base;
  async function request(
    profile: Profile,
    {
      refinement = "",
      previous = null,
      signal,
      scenario = "",
    }: RecommendationOptions = {},
  ): Promise<Outfit[]> {
    if (!profileComplete(profile))
      throw new Error("체형, TPO, 추구미를 먼저 선택해주세요.");
    if (sample) {
      await delay(config.demoDelayMs ?? 650, signal);
      if (scenario === "error")
        throw new Error("샘플 추천을 불러오지 못했어요. 다시 시도해주세요.");
      if (scenario === "empty") return [];
      return normalizeRecommendations(
        demoRecommendations(profile, refinement, previous),
      );
    }
    const controller = new AbortController();
    const cancel = () => controller.abort(signal?.reason);
    if (signal?.aborted) cancel();
    else signal?.addEventListener("abort", cancel, { once: true });
    const timer = setTimeout(
      () => controller.abort(new DOMException("Timeout", "TimeoutError")),
      config.timeoutMs || 20000,
    );
    try {
      const response = await fetcher(`${base}/recommendations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile,
          refinement: refinement || null,
          previousOutfit: previous,
        }),
        signal: controller.signal,
      });
      if (!response.ok)
        throw new Error(
          response.status === 429
            ? "요청이 잠시 많아요. 조금 뒤 다시 시도해주세요."
            : "추천을 불러오지 못했어요. 연결을 확인하고 다시 시도해주세요.",
        );
      return normalizeRecommendations(await response.json());
    } catch (error) {
      if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
      if (controller.signal.aborted)
        throw new Error("추천 응답이 늦어지고 있어요. 다시 시도해주세요.");
      if (error instanceof TypeError || error instanceof SyntaxError)
        throw new Error(
          "추천 서버에 연결하지 못했어요. 연결을 확인하고 다시 시도해주세요.",
        );
      throw error;
    } finally {
      clearTimeout(timer);
      signal?.removeEventListener("abort", cancel);
    }
  }
  return { sample, request };
}
