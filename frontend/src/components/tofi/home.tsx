"use client";

import { getCatalog } from "@/lib/tofi/catalog";
import { bodyComplete } from "@/lib/tofi/domain";
import { useTofi } from "@/lib/tofi/use-tofi";
import { Button, Heading, ProductImage } from "./ui";

const products = getCatalog().slice(0, 4);
const overview = [
  [
    "Body Type",
    <>
      이미 알고 있는 나의 체형을 바탕으로
      <br />
      어울리는 핏과 실루엣을 살펴봐요.
    </>,
  ],
  [
    "TPO",
    <>
      출근부터 여행까지.
      <br />
      오늘의 상황에 맞는 스타일을 찾아요.
    </>,
  ],
  [
    "추구미",
    <>
      원하는 분위기와 세부 취향으로
      <br />세 가지 셀렉션을 완성해요.
    </>,
  ],
] as const;

export function HomeScreen() {
  const { profile } = useTofi();
  const returning = bodyComplete(profile);
  return (
    <>
      <section className="welcome">
        <div className="welcome-inner">
          <div className="welcome-copy">
            <Heading
              title={
                <>
                  취향은 선명하게,
                  <br />
                  쇼핑은 단순하게.
                </>
              }
              description={
                <>
                  바디타입과 추구미를 바탕으로
                  <br className="desktop-break" /> T.P.O에 맞는 스타일을
                  제안합니다.
                </>
              }
            />
            <div className="welcome-action">
              <Button
                href={returning ? "/style/tpo" : "/style/body-type"}
                arrow
              >
                {returning ? "이어서 스타일 찾기" : "나만의 셀렉션 시작하기"}
              </Button>
              <p className="quiet">
                본인의 바디타입을 알고 계신 분을 위한 서비스
              </p>
            </div>
          </div>
          <div className="welcome-selection">
            <div className="selection-heading">
              <span>발표를 위한 미니멀 셀렉션</span>
              <span className="sample-tag">스타일 예시</span>
            </div>
            <div className="welcome-products">
              {products.map((product) => (
                <div key={product.id}>
                  <ProductImage product={product} />
                  <span>{product.category}</span>
                </div>
              ))}
            </div>
            <p className="welcome-note">
              여러 선택지 대신, 나에게 맞는 세 가지.
            </p>
          </div>
        </div>
      </section>
      <section className="how-it-works container" aria-label="토피 이용 순서">
        {overview.map(([title, description], index) => (
          <div key={title}>
            <span className="how-number">0{index + 1}</span>
            <h2>{title}</h2>
            <p>{description}</p>
          </div>
        ))}
      </section>
    </>
  );
}
