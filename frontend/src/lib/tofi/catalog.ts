import type {
  BodyType,
  Category,
  Filter,
  Mood,
  Product,
  ProductGroup,
  Profile,
} from "./types.ts";

export const BODY_TYPES: readonly BodyType[] = [
  "웨이브",
  "스트레이트",
  "내추럴",
];
export const OCCASIONS = [
  ["출근", "briefcase"],
  ["등교", "school"],
  ["면접", "file"],
  ["발표", "presentation"],
  ["데이트", "heart"],
  ["모임", "users"],
  ["경조사", "flower"],
  ["여행", "plane"],
  ["외출", "bag"],
  ["파티", "party"],
] as const;
export const MOODS: readonly {
  name: Mood;
  description: string;
  index: number;
}[] = [
  { name: "미니멀", description: "간결하고 세련된 무드", index: 0 },
  { name: "로맨틱", description: "부드럽고 섬세한 무드", index: 1 },
  { name: "캐주얼", description: "편안하고 자연스러운 무드", index: 2 },
  { name: "시크", description: "도시적이고 담백한 무드", index: 3 },
];
export const TAGS: readonly string[] = [
  "차분한 색감",
  "편한 착용감",
  "화사한 색감",
  "여유로운 핏",
  "허리선 강조",
  "노출 적게",
  "액세서리 포인트",
];
export const CATEGORIES: readonly Filter[] = [
  "전체",
  "상의",
  "하의",
  "아우터",
  "신발",
  "가방·액세서리",
];

const items: readonly (readonly [string, string, Category, number, number])[] =
  [
    ["knit", "아이보리 울 니트", "상의", 79000, 0],
    ["navy-pants", "네이비 스트레이트 팬츠", "하의", 129000, 1],
    ["brown-loafers", "브라운 레더 로퍼", "신발", 159000, 2],
    ["shoulder-bag", "레더 숄더백", "가방·액세서리", 189000, 3],
    ["blue-shirt", "소프트 블루 블라우스", "상의", 89000, 4],
    ["sand-pants", "샌드 테일러드 팬츠", "하의", 119000, 5],
    ["black-loafers", "블랙 레더 로퍼", "신발", 149000, 6],
    ["tote-bag", "에스프레소 토트백", "가방·액세서리", 169000, 7],
    ["cardigan", "토프 니트 카디건", "상의", 99000, 8],
    ["cotton-pants", "크림 코튼 팬츠", "하의", 89000, 9],
    ["sneakers", "아이보리 스니커즈", "신발", 89000, 10],
    ["skirt", "에스프레소 A라인 스커트", "하의", 99000, 11],
  ];

export function getCatalog(group: ProductGroup = "여성"): Product[] {
  return items
    .filter(([id]) => group !== "남성" || id !== "skirt")
    .map(([id, name, category, price, sprite]) => ({
      id: `${group === "남성" ? "m" : "w"}-${id}`,
      name: group === "남성" && id === "blue-shirt" ? "소프트 블루 셔츠" : name,
      category,
      price,
      sprite,
      imageUrl: null,
      url: null,
      sample: true,
    }));
}

export function freshProfile(): Profile {
  return {
    mode: "single",
    upper: "",
    lower: "",
    group: "여성",
    occasion: "",
    mood: "",
    tags: [],
  };
}
