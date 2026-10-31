"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { getSupabaseClient } from "@/lib/supabase/client";
import { safeReturnPath } from "@/lib/supabase/redirect";
import { actions } from "@/lib/tofi/store";
import { useTofi } from "@/lib/tofi/use-tofi";
import { Button, Heading } from "./ui";

export function AuthBridge() {
  const router = useRouter();
  useEffect(() => {
    const login = (event: Event) => router.push("/login?next=" + encodeURIComponent(safeReturnPath((event as CustomEvent<string>).detail)));
    window.addEventListener("tofi:login-required", login);
    const client = getSupabaseClient();
    if (!client) {
      void actions.syncAccount(null);
      return () => window.removeEventListener("tofi:login-required", login);
    }
    let active = true;
    const { data } = client.auth.onAuthStateChange((event, session) => {
      if (event === "TOKEN_REFRESHED") return;
      // Supabase callbacks run inside the auth lock; never await another auth call here.
      queueMicrotask(() => {
        if (active) void actions.syncAccount(session?.user.id || null);
      });
    });
    return () => {
      active = false;
      data.subscription.unsubscribe();
      window.removeEventListener("tofi:login-required", login);
    };
  }, [router]);
  return null;
}

export function AccountControl() {
  const state = useTofi();
  const [busy, setBusy] = useState(false);
  if (state.accountStatus === "loading")
    return (
      <span className="account-note" role="status">
        확인 중
      </span>
    );
  if (!state.member) return <Link href="/login">Google 로그인</Link>;
  return (
    <div className="account-control">
      <span className="account-name">{state.member.name}님</span>
      <button
        type="button"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          await actions.syncAccount(null);
          try {
            const client = getSupabaseClient();
            if (client) {
              let timer: ReturnType<typeof setTimeout> | undefined;
              try {
                await Promise.race([
                  client.auth.signOut({ scope: "local" }),
                  new Promise((_, reject) => {
                    timer = setTimeout(
                      () => reject(new Error("logout timeout")),
                      4000,
                    );
                  }),
                ]);
              } finally {
                clearTimeout(timer);
              }
            }
          } catch {
            /* Always remove this browser's cookies even if the Auth server is unavailable. */
          }
          try {
            const response = await fetch("/auth/logout", { method: "POST" });
            if (!response.ok) throw new Error("local logout failed");
          } catch {
            for (const entry of document.cookie.split(";")) {
              const name = entry.split("=")[0].trim();
              if (name.startsWith("sb-"))
                document.cookie = name + "=; Max-Age=0; Path=/; SameSite=Lax";
            }
          }
          // Discard the cached Supabase client and pending token refreshes after logout.
          // eslint-disable-next-line @next/next/no-location-assign-relative-destination
          window.location.assign("/");
        }}
      >
        로그아웃
      </button>
    </div>
  );
}

export function GoogleLoginScreen() {
  const state = useTofi();
  const query = useSearchParams();
  const router = useRouter();
  const next = safeReturnPath(query.get("next"));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    if (state.accountStatus === "member") router.replace(next);
  }, [state.accountStatus, router, next]);
  const callbackError = query.has("error")
    ? "Google 로그인을 완료하지 못했어요. 다시 시도해주세요."
    : "";
  return (
    <div className="container login-page">
      <Heading
        title="내 옷장을 이어서"
        description="Google 계정 하나로 가입하고 로그인해요."
      />
      <div className="login-panel">
        <p>
          마음에 든 상품을 내 계정에 저장하고,
          <br />
          다른 기기에서도 다시 찾아보세요.
        </p>
        <Button
          disabled={busy || state.accountStatus === "loading"}
          className="google-login-button"
          onClick={async () => {
            const client = getSupabaseClient();
            setError("");
            if (!client) {
              setError("로그인을 준비 중이에요. 잠시 후 다시 시도해주세요.");
              return;
            }
            setBusy(true);
            try {
              const response = await fetch(
                process.env.NEXT_PUBLIC_SUPABASE_URL + "/auth/v1/settings",
                {
                  headers: {
                    apikey:
                      process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || "",
                  },
                  cache: "no-store",
                },
              );
              const settings = await response.json();
              if (!response.ok || !settings.external?.google)
                throw new Error("Google 로그인 설정이 아직 완료되지 않았어요.");
              const redirect = new URL(
                "/auth/callback",
                window.location.origin,
              );
              redirect.searchParams.set("next", next);
              const { data, error } = await client.auth.signInWithOAuth({
                provider: "google",
                options: {
                  redirectTo: redirect.href,
                  skipBrowserRedirect: true,
                },
              });
              if (error || !data.url)
                throw new Error(
                  "Google 로그인에 연결하지 못했어요. 다시 시도해주세요.",
                );
              window.location.assign(data.url);
            } catch (error) {
              setError(
                error instanceof Error
                  ? error.message
                  : "Google 로그인에 연결하지 못했어요.",
              );
              setBusy(false);
            }
          }}
        >
          <span aria-hidden="true" className="google-mark">
            G
          </span>
          {busy ? "Google로 이동 중…" : "Google로 계속하기"}
        </Button>
        <p className="field-note">
          처음 로그인하면 회원 계정이 자동으로 만들어져요.
        </p>
        {error || callbackError ? (
          <p className="inline-error" role="alert">
            {error || callbackError}
          </p>
        ) : null}
        {state.accountError ? (
          <p className="inline-error" role="alert">
            {state.accountError}
          </p>
        ) : null}
        <Link href="/" className="login-back">
          스타일 먼저 살펴보기
        </Link>
      </div>
    </div>
  );
}
