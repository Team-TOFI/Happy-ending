import { normalizeWardrobe } from "./domain.ts";
import { record } from "./types.ts";
import type { Profile, SavedItem } from "./types.ts";
export interface Member {
  id: string;
  email: string;
  name: string;
  avatarUrl?: string | null;
}
export class AccountError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}
export interface AccountService {
  me(): Promise<Member>;
  list(): Promise<SavedItem[]>;
  save(id: string, profile: Profile, comment: string): Promise<SavedItem>;
  remove(id: string): Promise<void>;
}
export function createAccountService(
  token: () => Promise<string | null>,
  fetcher: typeof fetch = globalThis.fetch,
): AccountService {
  async function request(path: string, method = "GET", body?: unknown) {
    const access = await token();
    if (!access) throw new AccountError(401, "Google 로그인이 필요해요.");
    let response: Response;
    try {
      response = await fetcher("/api" + path, {
        method,
        headers: {
          Authorization: "Bearer " + access,
          ...(body ? { "Content-Type": "application/json" } : {}),
        },
        body: body ? JSON.stringify(body) : undefined,
        cache: "no-store",
      });
    } catch {
      throw new AccountError(
        503,
        "서버에 연결하지 못했어요. 다시 시도해주세요.",
      );
    }
    if (!response.ok)
      throw new AccountError(
        response.status,
        response.status === 401
          ? "로그인이 만료됐어요. 다시 로그인해주세요."
          : "옷장을 불러오지 못했어요. 다시 시도해주세요.",
      );
    return response.status === 204 ? null : response.json();
  }
  return {
    async me() {
      const user = record(await request("/auth/me"));
      if (
        typeof user.id !== "string" ||
        typeof user.email !== "string" ||
        typeof user.name !== "string"
      )
        throw new AccountError(502, "회원 정보를 확인할 수 없어요.");
      return user as unknown as Member;
    },
    async list() {
      const data = record(await request("/wardrobe"));
      if (!Array.isArray(data.items))
        throw new AccountError(502, "옷장 정보를 확인할 수 없어요.");
      return normalizeWardrobe(data.items);
    },
    async save(id, profile, comment) {
      const data = await request("/wardrobe/" + encodeURIComponent(id), "PUT", {
        profile,
        comment,
      });
      const items = normalizeWardrobe([data]);
      if (items.length !== 1)
        throw new AccountError(502, "저장한 상품을 확인할 수 없어요.");
      return items[0];
    },
    async remove(id) {
      await request("/wardrobe/" + encodeURIComponent(id), "DELETE");
    },
  };
}
