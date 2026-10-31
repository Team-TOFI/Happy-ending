"use client";

import Image from "next/image";
import Link from "next/link";
import { useState, type ReactNode } from "react";
import type { Product, Profile } from "@/lib/tofi/types";

const iconPaths = {
  arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
  back: <path d="M20 12H4m6-6-6 6 6 6" />,
  check: <path d="m5 12 4 4L19 6" />,
  heart: (
    <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z" />
  ),
  briefcase: (
    <>
      <rect x="3" y="7" width="18" height="14" rx="2" />
      <path d="M8 7V4h8v3m-13 6h18m-11 0v3h2v-3" />
    </>
  ),
  school: <path d="m2 9 10-5 10 5-10 5L2 9Zm4 2v7c4 3 8 3 12 0v-7m4-2v9" />,
  file: (
    <>
      <rect x="5" y="3" width="14" height="18" rx="2" />
      <path d="M8 8h8M8 12h8m-8 4h5" />
    </>
  ),
  presentation: <path d="M3 4h18M5 4v12h14V4m-7 12v5m0-5-5 5m5-5 5 5M8 9h8" />,
  users: (
    <>
      <circle cx="9" cy="7" r="3" />
      <path d="M3 21v-3a6 6 0 0 1 12 0v3H3ZM17 4a3 3 0 0 1 0 6m1 4a5 5 0 0 1 3 4v3h-3" />
    </>
  ),
  flower: (
    <path d="M12 12c-10 0-9-8-4-7 0-5 8-5 8 0 5-1 6 7-4 7Zm0 0v10m0-5c4 0 6-3 6-3m-6 6c-4 0-6-3-6-3" />
  ),
  plane: <path d="m21 3-6 18-4-8-8-4L21 3ZM11 13 21 3" />,
  bag: <path d="M5 7h14l2 14H3L5 7Zm3 0V5a4 4 0 0 1 8 0v2" />,
  party: (
    <path d="m4 20 5-14 9 9-14 5Zm9-15 2-3m3 6 4-1m-4 4 3 2M7 13l4 4m-2-7 5 5" />
  ),
  hanger: <path d="M10 6a2 2 0 1 1 3 2l-1 1v2L3 17v3h18v-3l-9-6" />,
  coins: (
    <>
      <ellipse cx="12" cy="5" rx="8" ry="3" />
      <path d="M4 5v5c0 4 16 4 16 0V5M4 10v5c0 4 16 4 16 0v-5M4 15v4c0 4 16 4 16 0v-4" />
    </>
  ),
  trousers: <path d="M7 3h10l3 18h-6l-2-12-2 12H4L7 3Zm0 4h10" />,
  dress: <path d="m8 3 2 5h4l2-5m-8 0-2 5 3 4-5 9h16l-5-9 3-4-2-5M9 12h6" />,
  shirt: <path d="m8 3-6 5 3 5 3-2v10h8V11l3 2 3-5-6-5-4 4-4-4Z" />,
  refresh: <path d="M20 8a8 8 0 1 0 0 8m0-13v5h-5" />,
};
export type IconName = keyof typeof iconPaths;
export function Icon({
  name,
  className = "",
}: {
  name: IconName;
  className?: string;
}) {
  return (
    <svg
      className={`icon ${className}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {iconPaths[name]}
    </svg>
  );
}
export function SelectionCheck() {
  return (
    <span className="selection-check">
      <Icon name="check" />
    </span>
  );
}
export function Heading({
  title,
  description,
  className = "",
}: {
  title: ReactNode;
  description?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`page-heading ${className}`}>
      <h1 id="page-title" tabIndex={-1}>
        {title}
      </h1>
      {description ? <p>{description}</p> : null}
    </div>
  );
}
interface ButtonProps {
  children: ReactNode;
  href?: string;
  variant?: "primary" | "secondary" | "text";
  disabled?: boolean;
  arrow?: boolean;
  className?: string;
  onClick?: () => void;
  type?: "button" | "submit";
  id?: string;
}
export function Button({
  children,
  href,
  variant = "primary",
  disabled = false,
  arrow = false,
  className = "",
  onClick,
  type = "button",
  id,
}: ButtonProps) {
  const content = (
    <>
      {children}
      {arrow ? <Icon name="arrow" /> : null}
    </>
  );
  const classes = `button ${variant} ${className}`;
  return href && !disabled ? (
    <Link href={href} className={classes} onClick={onClick} id={id}>
      {content}
    </Link>
  ) : (
    <button
      type={type}
      className={classes}
      disabled={disabled}
      onClick={onClick}
      id={id}
    >
      {content}
    </button>
  );
}
export const money = (value: number) => `${value.toLocaleString("ko-KR")}원`;
export function ProductImage({
  product,
  className = "",
}: {
  product: Product;
  className?: string;
}) {
  const [failedUrl, setFailedUrl] = useState<string | null>(null);
  if (product.imageUrl && failedUrl !== product.imageUrl)
    return (
      <Image
        className={`product-image ${className}`}
        src={product.imageUrl}
        alt={product.name}
        width={512}
        height={512}
        unoptimized
        onError={() => setFailedUrl(product.imageUrl)}
        referrerPolicy="no-referrer"
      />
    );
  if (product.sprite !== null)
    return (
      <span
        role="img"
        aria-label={product.name}
        className={`product-image product-sprite ${className}`}
        style={{
          backgroundPosition: `${((product.sprite % 4) / 3) * 100}% ${(Math.floor(product.sprite / 4) / 2) * 100}%`,
        }}
      />
    );
  return (
    <span
      role="img"
      aria-label={`${product.name} 이미지 없음`}
      className={`product-image image-fallback ${className}`}
    >
      <Icon name="hanger" />
    </span>
  );
}
export function SaveButton({
  product,
  saved,
  onSave,
  compact = false,
}: {
  product: Product;
  saved: boolean;
  onSave: () => void;
  compact?: boolean;
}) {
  return (
    <button
      type="button"
      className={`${compact ? "save-icon" : "button secondary save-button"} ${saved ? "is-saved" : ""}`}
      aria-pressed={saved}
      aria-label={`${product.name} ${saved ? "저장 취소" : "옷장에 담기"}`}
      onClick={onSave}
    >
      <Icon name="heart" />
      {!compact ? <span>{saved ? "담았어요" : "옷장에 담기"}</span> : null}
    </button>
  );
}
export function Stepper({ step, profile }: { step: number; profile: Profile }) {
  const steps = [
    ["/style/body-type", "Body Type"],
    ["/style/tpo", "TPO"],
    ["/style/mood", "추구미"],
  ];
  return (
    <nav className="stepper" aria-label="스타일 선택 단계">
      <ol>
        {steps.map(([href, label], index) => {
          const enabled =
            index === 0 ||
            (index === 1
              ? profile.upper && profile.lower
              : profile.upper && profile.lower && profile.occasion);
          const content = (
            <>
              <span className="step-number">
                {index < step ? <Icon name="check" /> : `0${index + 1}`}
              </span>
              <span>{label}</span>
            </>
          );
          return (
            <li
              key={href}
              className={
                index === step ? "current" : index < step ? "complete" : ""
              }
            >
              {enabled ? (
                <Link
                  href={href}
                  aria-current={index === step ? "step" : undefined}
                >
                  {content}
                </Link>
              ) : (
                <button type="button" disabled>
                  {content}
                </button>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
export function EmptyState({
  title,
  description,
  href = "/style/body-type",
  label = "스타일 찾기",
}: {
  title: string;
  description: string;
  href?: string;
  label?: string;
}) {
  return (
    <div className="empty-state">
      <Icon name="hanger" />
      <h2>{title}</h2>
      <p>{description}</p>
      <Button href={href} arrow>
        {label}
      </Button>
    </div>
  );
}
export function LoadingCards() {
  return (
    <>
      <div className="loading-header" role="status">
        선택한 조건으로 셀렉션을 고르고 있어요.
      </div>
      <div className="outfit-grid" aria-hidden="true">
        {[0, 1, 2].map((index) => (
          <div key={index} className="skeleton-card">
            <div className="skeleton-line wide" />
            <div className="skeleton-line" />
            <div className="skeleton-products">
              {[0, 1, 2, 3].map((i) => (
                <div key={i} />
              ))}
            </div>
            <div className="skeleton-line wide" />
          </div>
        ))}
      </div>
    </>
  );
}
