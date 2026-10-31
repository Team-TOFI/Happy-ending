"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { profileText } from "@/lib/tofi/domain";
import { actions, recommendationService } from "@/lib/tofi/store";
import { useTofi } from "@/lib/tofi/use-tofi";
import {
  Button,
  EmptyState,
  Heading,
  Icon,
  money,
  ProductImage,
  SaveButton,
  type IconName,
} from "./ui";

export function OutfitDetailScreen({ id }: { id: string }) {
  const state = useTofi();
  const [request, setRequest] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const outfit = state.outfits.find((outfit) => outfit.id === id);
  const profile = state.resultProfile;
  if (!state.ready)
    return (
      <div className="container detail-page">
        <Heading title="Tofi Pick" />
        <p className="loading-header" role="status">
          셀렉션을 불러오고 있어요.
        </p>
      </div>
    );
  if (!outfit || !profile)
    return (
      <div className="container detail-page">
        <Heading title="Tofi Pick" />
        <EmptyState
          title="먼저 셀렉션을 골라주세요"
          description="추천 결과에서 마음에 드는 코디의 아이템을 확인할 수 있어요."
          href={state.outfits.length ? "/picks" : "/style/body-type"}
        />
      </div>
    );
  const loading = state.pending?.kind === "refine";
  const lower =
    profile.group === "남성"
      ? "팬츠 바꾸기"
      : outfit.products.some((product) => product.id.endsWith("-skirt"))
        ? "팬츠로 바꾸기"
        : "스커트로 바꾸기";
  const quicks: [string, IconName][] = [
    ["더 캐주얼하게", "hanger"],
    ["예산 낮추기", "coins"],
    [lower, "trousers"],
  ];
  return (
    <div className="container detail-page">
      <Link className="back-link" href="/picks">
        <Icon name="back" />
        Tofi Pick으로 돌아가기
      </Link>
      <div className="detail-columns">
        <section className="detail-main">
          <Heading
            title={outfit.name}
            description={`${profile.occasion}에 어울리는, ${profile.mood} 무드의 셀렉션이에요.`}
          />
          <div className="detail-profile">
            <div>
              <strong>
                Profile <Icon name="check" />
              </strong>
              <p>{profileText(profile)}</p>
            </div>
            <div>
              <strong>
                TPO <Icon name="check" />
              </strong>
              <p>
                {profile.occasion} · {profile.mood}
                {profile.tags.length ? (
                  <>
                    <br />
                    {profile.tags.join(" · ")}
                  </>
                ) : null}
              </p>
            </div>
          </div>
          <div className="item-list-heading">
            <h2>
              선택된 아이템 <span>{outfit.products.length}가지</span>
            </h2>
            <p>{outfit.comment}</p>
          </div>
          <div className="product-rows">
            {outfit.products.map((product) => (
              <article key={product.id} className="product-row">
                <ProductImage product={product} />
                <div className="product-info">
                  <h3>{product.name}</h3>
                  <p>{money(product.price)}</p>
                  {product.sample ? (
                    <span className="sample-product">샘플 상품</span>
                  ) : null}
                </div>
                <div className="product-actions">
                  <SaveButton
                    product={product}
                    saved={state.wardrobe.some(
                      (item) => item.product.id === product.id,
                    )}
                    onSave={() =>
                      actions.save(product, profile, outfit.comment)
                    }
                  />
                  {product.url ? (
                    <a
                      className="button secondary product-link"
                      href={product.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      상품 보기 <Icon name="arrow" />
                    </a>
                  ) : (
                    <span className="unavailable-link">
                      {product.sample ? "시연용 상품" : "구매 링크 준비 중"}
                    </span>
                  )}
                </div>
              </article>
            ))}
          </div>
          <p className="total-price">
            <span>
              아이템 합계{recommendationService.sample ? " · 샘플 가격" : ""}
            </span>
            <strong>
              {money(
                outfit.products.reduce(
                  (sum, product) => sum + product.price,
                  0,
                ),
              )}
            </strong>
          </p>
          {outfit.revision ? (
            <p className="revision-note">
              <Icon name="check" />
              반영한 요청: {outfit.revision}
            </p>
          ) : null}
        </section>
        <aside className="refinement-panel">
          <h2>취향에 맞게 조정하기</h2>
          <p>
            원하는 방향이 있다면 알려주세요.
            <br />더 잘 맞는 스타일로 다시 제안해드릴게요.
          </p>
          <fieldset disabled={loading}>
            <legend>빠른 요청</legend>
            <div className="quick-requests">
              {quicks.map(([name, icon]) => (
                <button
                  key={name}
                  type="button"
                  className={`quick-request ${request === name ? "is-selected" : ""}`}
                  aria-pressed={request === name}
                  onClick={() => {
                    setRequest(name);
                    actions.clearError();
                  }}
                >
                  <Icon name={icon} />
                  <span>{name}</span>
                  <Icon name="arrow" />
                </button>
              ))}
            </div>
          </fieldset>
          <form
            id="refinement-form"
            onSubmit={async (event) => {
              event.preventDefault();
              if (!request.trim() || loading) return;
              if (await actions.refine(id, request)) setRequest("");
              inputRef.current?.focus({ preventScroll: true });
            }}
          >
            <label className="request-label" htmlFor="refinement-input">
              직접 요청하기
            </label>
            <div className="textarea-wrap">
              <textarea
                ref={inputRef}
                id="refinement-input"
                name="refinement"
                maxLength={300}
                value={request}
                onChange={(event) => setRequest(event.target.value)}
                placeholder="원하는 변경을 적어주세요"
                disabled={loading}
                aria-describedby="request-count refinement-help"
              />
              <span id="request-count">{request.length} / 300</span>
            </div>
            <p className="field-note" id="refinement-help">
              체형·TPO·추구미는 그대로 유지해요.
            </p>
            {state.error ? (
              <p className="inline-error" role="alert">
                {state.error}
              </p>
            ) : null}
            <Button
              type="submit"
              className="full-width"
              disabled={!request.trim() || loading}
              arrow
            >
              {loading
                ? "스타일을 다시 고르고 있어요…"
                : "이 조건으로 다시 고르기"}
            </Button>
          </form>
          {loading ? (
            <p className="loading-note" role="status">
              기존 셀렉션을 유지하며 조정하고 있어요.
            </p>
          ) : null}
        </aside>
      </div>
    </div>
  );
}
