"use client";

import { useState } from "react";
import { CATEGORIES } from "@/lib/tofi/catalog";
import { bodyComplete, profileText } from "@/lib/tofi/domain";
import { actions } from "@/lib/tofi/store";
import type { Filter } from "@/lib/tofi/types";
import { useTofi } from "@/lib/tofi/use-tofi";
import {
  Button,
  EmptyState,
  Heading,
  Icon,
  money,
  ProductImage,
  SaveButton,
} from "./ui";

const dateFormat = new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul" });
export function WardrobeScreen() {
  const state = useTofi();
  const [filter, setFilter] = useState<Filter>("전체");
  const all = state.wardrobe;
  const items = all.filter(
    (item) => filter === "전체" || item.product.category === filter,
  );
  return (
    <div className="container wardrobe-page">
      <div className="wardrobe-heading">
        <Heading
          title="내가 고른 셀렉션"
          description="마음에 들어 담아둔 상품을 모았어요."
        />
        <Button
          href={bodyComplete(state.profile) ? "/style/tpo" : "/style/body-type"}
          arrow
        >
          토피 PICK
        </Button>
      </div>
      <div className="wardrobe-toolbar">
        <h2>
          담아둔 상품 <span>{all.length}</span>
        </h2>
        <div className="filter-list" role="group" aria-label="상품 분류">
          {CATEGORIES.map((category, index) => (
            <button
              key={category}
              id={`wardrobe-filter-${index}`}
              type="button"
              className={`filter-button ${filter === category ? "is-selected" : ""}`}
              aria-pressed={filter === category}
              onClick={() => setFilter(category)}
            >
              {category}
              <span>
                {category === "전체"
                  ? all.length
                  : all.filter((item) => item.product.category === category)
                      .length}
              </span>
            </button>
          ))}
        </div>
      </div>
      {!state.ready ? (
        <p className="loading-header" role="status">
          저장한 옷장을 불러오고 있어요.
        </p>
      ) : all.length === 0 ? (
        <EmptyState
          title="아직 담아둔 상품이 없어요"
          description={
            "마음에 드는 아이템의 하트를 눌러보세요.\n나중에 다시 보고 싶은 상품을 이곳에 모아둘게요."
          }
          href={state.outfits.length ? "/picks" : "/style/body-type"}
          label="셀렉션 살펴보기"
        />
      ) : items.length === 0 ? (
        <div className="empty-state">
          <Icon name="hanger" />
          <h2>이 분류에 담긴 상품이 없어요</h2>
          <p>다른 분류를 살펴보거나 새로운 아이템을 담아보세요.</p>
          <Button onClick={() => setFilter("전체")} arrow>
            전체 상품 보기
          </Button>
        </div>
      ) : (
        <div className="wardrobe-grid">
          {items.map(({ product, profile, comment, savedAt }) => (
            <article key={product.id} className="wardrobe-card">
              <ProductImage product={product} />
              <div className="wardrobe-info">
                <span className="product-category">{product.category}</span>
                <h3>{product.name}</h3>
                <p className="wardrobe-price">{money(product.price)}</p>
                <details className="saved-memo">
                  <summary>
                    <Icon name="file" />
                    추천 메모
                  </summary>
                  <div>
                    <p>{profileText(profile)}</p>
                    <p>
                      {[profile.occasion, profile.mood, ...profile.tags]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                    <p>{comment}</p>
                    <time dateTime={savedAt}>
                      {dateFormat.format(new Date(savedAt))} 저장
                    </time>
                  </div>
                </details>
              </div>
              <SaveButton
                product={product}
                saved
                compact
                onSave={() => {
                  actions.save(product, profile, comment);
                  document
                    .getElementById(
                      `wardrobe-filter-${CATEGORIES.indexOf(filter)}`,
                    )
                    ?.focus({ preventScroll: true });
                }}
              />
            </article>
          ))}
        </div>
      )}
      <p className="wardrobe-note">
        내 옷장은 관심 상품을 보관하는 공간이에요. 같은 브라우저에서 저장한
        상품을 다시 볼 수 있어요.
      </p>
    </div>
  );
}
