"use client";

import { profileComplete, profileText } from "@/lib/tofi/domain";
import { actions } from "@/lib/tofi/store";
import type { Profile } from "@/lib/tofi/types";
import { useTofi } from "@/lib/tofi/use-tofi";
import {
  Button,
  EmptyState,
  Heading,
  Icon,
  LoadingCards,
  ProductImage,
} from "./ui";

export function Conditions({ profile: p }: { profile: Profile }) {
  return (
    <div className="conditions">
      <strong>선택한 조건</strong>
      <div className="condition-tags">
        <span>{profileText(p)}</span>
        <span>{p.occasion}</span>
        <span>{p.mood}</span>
        {p.tags.map((tag) => (
          <span key={tag}>{tag}</span>
        ))}
      </div>
      <Button href="/style/body-type" variant="text" arrow>
        조건 수정
      </Button>
    </div>
  );
}

export function PicksScreen() {
  const state = useTofi();
  const profile = state.resultProfile || state.profile;
  const loading = !state.ready || state.pending?.kind === "recommend";
  return (
    <div className="container results-page">
      <Heading
        title="Tofi Pick"
        description="지금의 일상과 취향에 맞춰, 고민 없이 입을 수 있는 셀렉션을 제안해요."
      />
      {profileComplete(profile) ? <Conditions profile={profile} /> : null}
      <section aria-label="추천 셀렉션" aria-busy={loading}>
        {loading ? (
          <LoadingCards />
        ) : state.error ? (
          <div className="error-state" role="alert">
            <Icon name="refresh" />
            <h2>셀렉션을 가져오지 못했어요</h2>
            <p>{state.error}</p>
            <Button
              onClick={() => {
                void actions.recommend(profile);
              }}
              arrow
            >
              다시 시도하기
            </Button>
            <Button href="/style/body-type" variant="text">
              조건 수정하기
            </Button>
          </div>
        ) : state.outfits.length ? (
          <>
            <div className="outfit-grid">
              {state.outfits.map((outfit, index) => (
                <article
                  key={outfit.id}
                  className={`outfit-card ${index === 0 ? "first-pick" : ""}`}
                >
                  <div className="outfit-number">0{index + 1}</div>
                  <div className="outfit-content">
                    <h2>{outfit.name}</h2>
                    <p className="outfit-comment">{outfit.comment}</p>
                    <div className="outfit-products">
                      {outfit.products.map((product) => (
                        <div key={product.id} className="outfit-product">
                          <ProductImage product={product} />
                          <span>{product.name}</span>
                        </div>
                      ))}
                    </div>
                    <Button
                      href={`/picks/${encodeURIComponent(outfit.id)}`}
                      variant={index === 0 ? "primary" : "secondary"}
                      className="full-width"
                      arrow
                    >
                      아이템 확인하기
                    </Button>
                  </div>
                </article>
              ))}
            </div>
            {state.outfits.length < 3 ? (
              <p className="field-note">
                현재 조건에 맞는 셀렉션만 보여드려요. 조건을 바꾸면 다른
                스타일도 찾을 수 있어요.
              </p>
            ) : null}
          </>
        ) : (
          <EmptyState
            title={
              state.requested
                ? "조건에 맞는 셀렉션을 찾지 못했어요"
                : "아직 셀렉션이 없어요"
            }
            description={
              state.requested
                ? "선택한 조건을 바꾸어 다시 찾아보세요."
                : "체형·상황·취향을 골라 나만의 스타일을 찾아보세요."
            }
            label={state.requested ? "조건 수정하기" : "스타일 찾기"}
          />
        )}
      </section>
    </div>
  );
}
