"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, type ReactNode } from "react";
import { bodyComplete } from "@/lib/tofi/domain";
import { actions, recommendationService } from "@/lib/tofi/store";
import { useTofi } from "@/lib/tofi/use-tofi";

export function TofiShell({ children }: { children: ReactNode }) {
  const state = useTofi();
  const pathname = usePathname();
  const mainRef = useRef<HTMLElement>(null);
  useEffect(() => {
    actions.cancelOutside(pathname);
    document.getElementById("page-title")?.focus({ preventScroll: true });
  }, [pathname]);

  return (
    <div className="tofi-shell">
      <a
        className="skip-link"
        href="#main"
        onClick={(event) => {
          event.preventDefault();
          mainRef.current?.focus();
        }}
      >
        본문 바로가기
      </a>
      <header className="site-header">
        <div className="header-inner">
          <Link href="/" className="wordmark" aria-label="tofi 홈">
            tofi
            <span className="logo-dot" />
          </Link>
          <nav aria-label="주 메뉴">
            <Link
              href={
                bodyComplete(state.profile) ? "/style/tpo" : "/style/body-type"
              }
              aria-current={
                pathname !== "/" && pathname !== "/wardrobe"
                  ? "page"
                  : undefined
              }
            >
              스타일 찾기
            </Link>
            <Link
              href="/wardrobe"
              aria-current={pathname === "/wardrobe" ? "page" : undefined}
            >
              내 옷장
              {state.wardrobe.length ? (
                <span className="nav-count">{state.wardrobe.length}</span>
              ) : null}
            </Link>
          </nav>
        </div>
      </header>
      {state.storageUnavailable ? (
        <div className="storage-notice" role="status">
          브라우저 저장 공간을 사용할 수 없어요. 지금 선택은 유지되지만
          새로고침하면 사라질 수 있어요.
        </div>
      ) : null}
      <main id="main" ref={mainRef} tabIndex={-1}>
        {children}
      </main>
      <footer className="site-footer container">
        <Link className="footer-brand" href="/">
          tofi
        </Link>
        <p>
          {recommendationService.sample
            ? "상품·가격·이미지·코멘트는 시연용 예시입니다."
            : "선택한 조건을 바탕으로 제안하는 나만의 셀렉션"}
        </p>
        <span>To fit your everyday.</span>
      </footer>
      {state.toast ? (
        <div className="toast" role="status" aria-live="polite">
          {state.toast}
        </div>
      ) : null}
    </div>
  );
}
