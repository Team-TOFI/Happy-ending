"use client";

import { useRouter } from "next/navigation";
import { BODY_TYPES, MOODS, OCCASIONS, TAGS } from "@/lib/tofi/catalog";
import {
  bodyComplete,
  chooseType,
  normalizeProfile,
  profileText,
  toggleTag,
} from "@/lib/tofi/domain";
import { actions } from "@/lib/tofi/store";
import type { Profile } from "@/lib/tofi/types";
import { useTofi } from "@/lib/tofi/use-tofi";
import {
  Button,
  EmptyState,
  Heading,
  Icon,
  SelectionCheck,
  Stepper,
} from "./ui";

function TypeOptions({
  profile,
  part,
  title,
}: {
  profile: Profile;
  part: "upper" | "lower";
  title: string;
}) {
  const lower = part === "lower";
  return (
    <fieldset className="type-field">
      <legend>{title}</legend>
      <div className="type-grid">
        {BODY_TYPES.map((type, index) => {
          const checked = profile[part] === type;
          return (
            <label
              key={type}
              className={`visual-option ${checked ? "is-selected" : ""}`}
            >
              <input
                type="radio"
                name={part}
                value={type}
                checked={checked}
                onChange={() =>
                  actions.updateProfile(chooseType(profile, part, type))
                }
              />
              <span
                className="body-illustration"
                aria-hidden="true"
                style={{
                  backgroundPosition: `${index * 50}% ${lower ? 100 : 0}%`,
                  backgroundSize: `300% ${lower ? 180 : 240}%`,
                }}
              />
              <span className="option-caption">{type}</span>
              {checked ? <SelectionCheck /> : null}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

function ProfilePanel({ profile: p }: { profile: Profile }) {
  return (
    <aside className="profile-panel" aria-label="선택한 프로필">
      <h2>Profile</h2>
      <p className="quiet">직접 선택한 나의 스타일 프로필</p>
      <dl className="checklist">
        {[
          ["상체 타입", p.upper],
          ["하체 타입", p.lower],
          ["상품군", p.group],
        ].map(([label, value]) => (
          <div key={label}>
            <dt>
              <span className={`profile-check ${value ? "checked" : ""}`}>
                {value ? <Icon name="check" /> : null}
              </span>
              {label}
            </dt>
            <dd>{value || "선택 전"}</dd>
          </div>
        ))}
      </dl>
      <fieldset className="group-field">
        <legend>보고 싶은 상품군</legend>
        <div className="group-options">
          {(["여성", "남성"] as const).map((group, index) => (
            <label
              key={group}
              className={`group-option ${p.group === group ? "is-selected" : ""}`}
            >
              <input
                type="radio"
                name="group"
                value={group}
                checked={p.group === group}
                onChange={() => actions.updateProfile({ ...p, group })}
              />
              <Icon name={index ? "shirt" : "dress"} />
              <span>{group}</span>
              {p.group === group ? <SelectionCheck /> : null}
            </label>
          ))}
        </div>
      </fieldset>
      <p className="small-note">
        그림은 선택을 돕기 위한 예시이며,
        <br />
        체형을 진단하는 기능은 제공하지 않아요.
      </p>
    </aside>
  );
}

export function BodyTypeScreen() {
  const { profile: p } = useTofi();
  return (
    <div className="container form-page">
      <Stepper step={0} profile={p} />
      <div className="form-columns">
        <section>
          <Heading title="Body Type" description="내 체형을 선택합니다." />
          <fieldset className="mode-field">
            <legend>바디타입 선택 방식</legend>
            <div className="segmented">
              {(
                [
                  ["single", "단일 타입"],
                  ["mix", "상하체 믹스"],
                ] as const
              ).map(([mode, label]) => (
                <label
                  key={mode}
                  className={p.mode === mode ? "is-selected" : ""}
                >
                  <input
                    type="radio"
                    name="mode"
                    value={mode}
                    checked={p.mode === mode}
                    onChange={() =>
                      actions.updateProfile(normalizeProfile({ ...p, mode }))
                    }
                  />
                  {label}
                </label>
              ))}
            </div>
          </fieldset>
          <TypeOptions
            profile={p}
            part="upper"
            title={p.mode === "mix" ? "상체 타입" : "내 바디타입"}
          />
          {p.mode === "mix" ? (
            <TypeOptions profile={p} part="lower" title="하체 타입" />
          ) : (
            <p className="field-note">상체와 하체에 같은 타입이 적용돼요.</p>
          )}
        </section>
        <ProfilePanel profile={p} />
      </div>
      <div className="form-actions">
        <Button href="/" variant="secondary">
          이전
        </Button>
        <span className="action-helper">
          {bodyComplete(p)
            ? "선택한 프로필로 다음 단계를 이어가요."
            : p.mode === "mix"
              ? "상체와 하체 타입을 각각 골라주세요."
              : "바디타입 한 가지를 골라주세요."}
        </span>
        <Button href="/style/tpo" disabled={!bodyComplete(p)} arrow>
          TPO 선택하기
        </Button>
      </div>
    </div>
  );
}

function Recipe({ profile: p }: { profile: Profile }) {
  return (
    <aside className="recipe-panel">
      <h2>OOTD Recipe</h2>
      <p>
        선택한 내용을 바탕으로
        <br />
        3가지 스타일을 제안할게요
      </p>
      <dl className="recipe-list">
        <div>
          <dt>Body Type</dt>
          <dd>{profileText(p)}</dd>
        </div>
        <div>
          <dt>상품군</dt>
          <dd>{p.group}</dd>
        </div>
        <div>
          <dt>TPO</dt>
          <dd>{p.occasion || "선택 전"}</dd>
        </div>
      </dl>
    </aside>
  );
}

function RestoreProfile({ title }: { title: string }) {
  return (
    <div className="container form-page">
      <Heading title={title} />
      <p className="loading-header" role="status">
        저장한 스타일 프로필을 불러오고 있어요.
      </p>
    </div>
  );
}

export function TpoScreen() {
  const { profile: p, ready } = useTofi();
  if (!ready) return <RestoreProfile title="TPO" />;
  if (!bodyComplete(p))
    return (
      <div className="container form-page">
        <Heading title="TPO" />
        <EmptyState
          title="먼저 체형을 선택해주세요"
          description="선택한 체형을 바탕으로 다음 단계를 이어갈게요."
        />
      </div>
    );
  return (
    <div className="container form-page">
      <Stepper step={1} profile={p} />
      <div className="form-columns">
        <section>
          <Heading title="TPO" description="입을 상황 하나를 골라주세요." />
          <fieldset>
            <legend className="sr-only">입을 상황</legend>
            <div className="occasion-grid">
              {OCCASIONS.map(([name, icon]) => (
                <label
                  key={name}
                  className={`occasion-option ${p.occasion === name ? "is-selected" : ""}`}
                >
                  <input
                    type="radio"
                    name="occasion"
                    value={name}
                    checked={p.occasion === name}
                    onChange={() =>
                      actions.updateProfile({ ...p, occasion: name })
                    }
                  />
                  <Icon name={icon} />
                  <span>{name}</span>
                  {p.occasion === name ? <SelectionCheck /> : null}
                </label>
              ))}
            </div>
          </fieldset>
        </section>
        <Recipe profile={p} />
      </div>
      <div className="form-actions">
        <Button href="/style/body-type" variant="secondary">
          이전
        </Button>
        <span className="action-helper">
          {p.occasion
            ? `${p.occasion}에 입을 스타일을 찾아볼게요.`
            : "TPO를 선택하면 다음으로 이동할 수 있어요."}
        </span>
        <Button href="/style/mood" disabled={!p.occasion} arrow>
          추구미 선택하기
        </Button>
      </div>
    </div>
  );
}

export function MoodScreen() {
  const { profile: p, ready, pending } = useTofi();
  const router = useRouter();
  if (!ready) return <RestoreProfile title="추구미" />;
  if (!bodyComplete(p) || !p.occasion)
    return (
      <div className="container form-page">
        <Heading title="추구미" />
        <EmptyState
          title="체형과 TPO를 먼저 골라주세요"
          description="입을 상황을 선택하면 원하는 분위기를 고를 수 있어요."
          href={bodyComplete(p) ? "/style/tpo" : "/style/body-type"}
        />
      </div>
    );
  return (
    <form
      className="container form-page mood-page"
      onSubmit={(event) => {
        event.preventDefault();
        if (!p.mood || pending) return;
        const scenario =
          new URLSearchParams(window.location.search).get("demo") || "";
        void actions.recommend(p, scenario);
        router.push("/picks");
      }}
    >
      <Stepper step={2} profile={p} />
      <Heading
        title="어떤 분위기로 입고 싶나요?"
        description={
          <>
            {profileText(p)} <span className="text-divider">/</span>{" "}
            {p.occasion}
          </>
        }
      />
      <fieldset>
        <legend className="sr-only">추구미 한 가지</legend>
        <div className="mood-grid">
          {MOODS.map(({ name, description, index }) => (
            <label
              key={name}
              className={`mood-option ${p.mood === name ? "is-selected" : ""}`}
            >
              <input
                type="radio"
                name="mood"
                value={name}
                checked={p.mood === name}
                onChange={() => actions.updateProfile({ ...p, mood: name })}
              />
              <span
                className="mood-photo"
                aria-hidden="true"
                style={{ backgroundPosition: `${(index / 3) * 100}% 50%` }}
              />
              <span className="mood-caption">
                <strong>{name}</strong>
                <span>{description}</span>
              </span>
              {p.mood === name ? <SelectionCheck /> : null}
            </label>
          ))}
        </div>
      </fieldset>
      <fieldset className="tag-field">
        <legend>
          세부 취향 <span aria-live="polite">{p.tags.length} / 3</span>
        </legend>
        <p id="tags-help">
          원하는 무드를 더 자세히 알려주세요. 최대 세 개를 선택할 수 있습니다.
        </p>
        <div className="tags" aria-describedby="tags-help">
          {TAGS.map((tag) => {
            const checked = p.tags.includes(tag);
            const disabled = p.tags.length >= 3 && !checked;
            return (
              <label
                key={tag}
                className={`tag-option ${checked ? "is-selected" : ""} ${disabled ? "is-disabled" : ""}`}
              >
                <input
                  type="checkbox"
                  name="tag"
                  value={tag}
                  checked={checked}
                  disabled={disabled}
                  onChange={() =>
                    actions.updateProfile({
                      ...p,
                      tags: toggleTag(p.tags, tag),
                    })
                  }
                />
                <span className="tag-check">
                  {checked ? <Icon name="check" /> : null}
                </span>
                {tag}
              </label>
            );
          })}
        </div>
      </fieldset>
      <div className="form-actions">
        <Button href="/style/tpo" variant="secondary">
          이전
        </Button>
        <span className="action-helper">
          {!p.mood
            ? "추구미 한 가지를 골라주세요."
            : "세부 취향은 선택하지 않아도 괜찮아요."}
        </span>
        <Button type="submit" disabled={!p.mood || !!pending} arrow>
          토피 PICK
        </Button>
      </div>
    </form>
  );
}
