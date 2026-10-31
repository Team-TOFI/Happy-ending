---
name: TOFI
description: Calm, sophisticated style selection in light toffee, cream, and espresso.
colors:
  cream: "#faf7f2"
  paper: "#fffdf9"
  toffee: "#bd9876"
  toffee-light: "#e9d9c7"
  sand: "#f0e8de"
  espresso: "#3c2a22"
  action: "#634632"
  action-hover: "#4e3526"
  muted: "#756457"
  border: "#d9cbbd"
  border-strong: "#9b7b60"
  error: "#974127"
  error-surface: "#fcf0e9"
typography:
  display:
    fontFamily: "'Segoe UI', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"
    fontSize: "48px"
    fontWeight: 600
    lineHeight: 1.45
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "'Segoe UI', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"
    fontSize: "40px"
    fontWeight: 650
    lineHeight: 1.35
    letterSpacing: "-0.035em"
  title:
    fontFamily: "'Segoe UI', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"
    fontSize: "28px"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-0.02em"
  outfit-title:
    fontFamily: "'Segoe UI', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"
    fontSize: "22px"
    fontWeight: 650
    lineHeight: 1.35
    letterSpacing: "-0.025em"
  body:
    fontFamily: "'Segoe UI', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "'Segoe UI', 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.45
rounded:
  radius: "12px"
  button-radius: "7px"
  option-radius: "8px"
  support-radius: "6px"
  image-radius: "4px"
spacing:
  space-1: "4px"
  space-2: "8px"
  space-3: "12px"
  space-4: "16px"
  space-6: "24px"
  space-8: "32px"
  space-12: "48px"
components:
  button-primary:
    backgroundColor: "{colors.action}"
    textColor: "{colors.paper}"
    typography: "{typography.label}"
    rounded: "{rounded.button-radius}"
    padding: "13px 24px"
  button-primary-hover:
    backgroundColor: "{colors.action-hover}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.action}"
    typography: "{typography.label}"
    rounded: "{rounded.button-radius}"
    padding: "13px 24px"
  button-secondary-hover:
    backgroundColor: "{colors.sand}"
  button-text:
    backgroundColor: "transparent"
    textColor: "{colors.action}"
    typography: "{typography.label}"
    rounded: "{rounded.button-radius}"
    padding: "13px 0"
  button-disabled:
    backgroundColor: "{colors.sand}"
    textColor: "{colors.muted}"
  textarea:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.espresso}"
    rounded: "{rounded.button-radius}"
    padding: "15px 15px 36px"
    width: "100%"
  tag:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.espresso}"
    rounded: "{rounded.support-radius}"
    padding: "12px 16px"
  tag-selected:
    backgroundColor: "{colors.sand}"
  profile-panel:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.espresso}"
    rounded: "{rounded.radius}"
    padding: "28px"
  outfit-card:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.espresso}"
    rounded: "{rounded.radius}"
  save-button-saved:
    backgroundColor: "{colors.toffee-light}"
    textColor: "{colors.action}"
    rounded: "{rounded.button-radius}"
    padding: "9px 16px"
---

# Design System: TOFI

## Overview

**Creative North Star: "Calm, sophisticated boutique"**

TOFI uses the user's confirmed light toffee, cream, and espresso direction to create a private, refined boutique mood. Light surfaces, warm hairline borders, small product images, and concise information keep the selection process calm and approachable.

The implemented system uses one native sans family across Korean and English. Hierarchy comes from size, weight, spacing, and tonal surfaces. This records the Next.js frontend in `src/app/globals.css` and `src/components/tofi/`; the v3 page compositions and confirmed copy remain governed by `docs/surface-brief.md` and `PRODUCT.md`.

**Key Characteristics:**
- Light cream and paper surfaces with restrained toffee emphasis.
- Espresso text and dark brown actions with clear contrast.
- One sans family, concise text, and small contained product imagery.
- Thin warm borders, modest rounding, and almost flat surfaces.
- Explicit selected, saved, focus, disabled, and feedback states.

## Colors

The palette is warm and light; darker browns carry readable text and actions.

### Primary

- **Toffee** (`toffee`): the wordmark dot and active navigation underline.
- **Light Toffee** (`toffee-light`): the welcome region, selected mode, completed step markers, saved button, and first recommendation header.
- **Action Brown** (`action`): primary buttons, interactive text, selected checkmarks, caret, and keyboard focus outline. **Deep Action Brown** (`action-hover`) darkens an enabled primary button on hover.

### Neutral

- **Cream** (`cream`): the page canvas. **Paper** (`paper`): header, cards, option tiles, and fields, as well as text on dark actions.
- **Sand** (`sand`): ordinary selected tiles and tags, quiet summaries, disabled buttons, placeholders, and secondary-button hover.
- **Espresso** (`espresso`): primary text and the feedback toast. **Muted Brown** (`muted`): secondary copy, notes, and supplementary counts.
- **Warm Border** (`border`): default one-pixel divisions and outlines. **Strong Border** (`border-strong`): hover, selected boundaries, and outlined actions.

The semantic error pair is **Error Brown** (`error`) on **Error Paper** (`error-surface`), used for the inline alert. Browser text selection uses Light Toffee with Espresso text.

**The Light Surface Rule.** Keep the broad page and card surfaces light. Reserve the dark browns for text, actions, selected marks, and transient feedback.

## Typography

**Display and Body Font:** the native sans stack recorded in the frontmatter. The system font choice is deliberate for this functional Operate surface; do not add a second display family as routine polish.

The default root size is the body role. Headings balance their lines; Korean paragraphs preserve words where possible and allow long content to wrap. Main heading descriptions are limited to (75ch). Numeric steps, counts, and prices use tabular numerals where the source specifies them.

### Hierarchy

- **Display:** the welcome heading uses the `display` role. Its responsive sizes are (39px) at widths up to (1150px), (42px) up to (820px), and (33px) with line height (1.5) up to (540px). These are explicit breakpoint values, not a fluid clamp.
- **Headline:** the normal page heading uses `headline`; it becomes (30px) on small screens. Detail and mood pages retain their smaller source-specific overrides.
- **Title:** summary-panel headings use `title`. Outfit headings use `outfit-title`, with size adjustments for the result-card layout. Supporting section headings commonly use (20–24px) at weight (600).
- **Body:** `body` supplies the base reading rhythm. Page descriptions use (17px) and line height (1.8) on desktop; component copy commonly uses (13–15px) and line height (1.8–1.9).
- **Label:** buttons use `label`. Navigation uses (15px) at regular weight and (600) for the current page. Compact product captions, sample disclosures, and notes use smaller source-specific sizes rather than a new typeface.
- **Wordmark:** the text wordmark is (44px), weight (500), line height (1), tracking (-0.04em); it becomes (36px) on small screens.

**The Single Family Rule.** Preserve the same native sans stack across headings, controls, and body copy; express hierarchy with the established sizes and weights.

## Layout

The normal content container is centered with a maximum width of (1304px) and desktop side gutters of (56px). The header has a wider maximum of (1416px). The header is (88px) tall. The defined spacing primitives form a four-pixel rhythm, supplemented by observed component values such as (20px) grid gaps, (28px) panel padding, and (56px) column gaps.

Desktop input screens place the main selection area beside a summary, using a (1.65:1) grid with a (300px) minimum summary width and a (56px) gap. Detail uses a (1.85:1) grid with a (48px) gap. Mood tiles use four columns; result and wardrobe grids use three. Outfit products use a two-by-two grid. Product imagery stays contained; mood photography crops into the option frame.

Responsive behavior follows the source media queries:

- **Up to (1150px):** side gutters become (32px); columns, gaps, and padding tighten. The wardrobe becomes two columns.
- **Up to (820px):** welcome, form, result, and detail columns stack; mood remains two columns. The profile panel briefly uses two internal columns. The recipe summary changes from a left divider to a Sand panel. Result cards become one column, while wardrobe cards remain in two columns.
- **Up to (540px):** side gutters become (20px), header height becomes (72px), and type and padding compact. Profile content returns to a single block. Form actions share one row with a flexible primary action. Wardrobe cards stack their own image and copy internally while the grid stays two columns.
- **From (1600px):** only the welcome section receives the larger source vertical padding (96px above, 84px below).

The app supports a minimum viewport width of (320px). Preserve content order and visible selection feedback when rearranging columns.

## Elevation & Depth

Depth comes mainly from Cream, Paper, Sand, and Light Toffee surfaces plus thin borders. Ordinary buttons, cards, summaries, and option tiles have no box shadow. Selection changes tone and boundary; it does not lift a card.

### Shadow Vocabulary

- **Toast feedback** (`0 6px 24px #3c2a2220`): the single ambient shadow beneath the fixed, dark feedback message.

**The Quiet Depth Rule.** Use borders and tonal separation for persistent surfaces; retain the ambient shadow for transient toast feedback.

## Shapes

Panels, outfit cards, and wardrobe cards use the `radius` primitive. Buttons, textareas, and quick requests use `button-radius`. Option tiles and small feedback surfaces use `option-radius`; tags, segmented outlines, and many product-image frames use `support-radius`. Small inner image frames use `image-radius`.

Borders are normally one pixel. Round checkmarks, step numbers, the wordmark dot, and compact save controls are circular. Condition summaries use pill ends (30px radius). These shapes communicate state and grouping; the main actions remain modest rounded rectangles.

## Components

### Buttons

Actions are compact, legible, and stationary. The base button has a minimum height of (50px), centered inline content, a (20px) icon gap, and the padding and typography recorded in the frontmatter. Primary uses Action Brown on Paper; secondary uses a transparent fill, Strong Border, and Action Brown text. The text variant removes horizontal padding and underlines on hover.

Enabled primary hover uses Deep Action Brown; enabled secondary hover uses Sand. Disabled buttons use Sand, Muted Brown, Warm Border, and a not-allowed cursor. State colors transition over (180ms) with `ease-out`; no hover lift is implemented.

### Selection controls and tags

Body, occasion, mood, and product-group choices use real radio inputs inside labeled tiles. Preference tags use checkboxes; wardrobe filters and quick requests expose pressed state on buttons. Ordinary selected choices use Sand and Strong Border, plus a circular check where applicable. The segmented mode control uses Light Toffee instead. Selected preference tags fill their small check circle with Action Brown and a Paper checkmark. At the selection limit, unselected tags become disabled and retain a Cream surface.

Preference tags wrap in a row with a (10px) gap, reducing to (8px) on small screens. Their desktop minimum height is (47px), reducing to (44px). Summary condition pills are read-only and must not be confused with these selectable controls.

### Cards and summaries

Cards use Paper, Warm Border, the panel radius, and no shadow. The profile panel has the frontmatter padding, a checklist of selected values, and product-group controls. The recipe summary uses a left divider on desktop and a filled Sand panel when stacked. Outfit cards separate the numeric header from their content; the first recommendation uses a stronger outer border and Light Toffee header. The card's content padding is (22px) on desktop with explicit responsive overrides. Small product images remain the focus of the two-by-two item group.

Wardrobe cards pair a small image with product information and an expandable recommendation memo. On small screens the image moves above the text. The memo uses a visible disclosure control, underline, and plus/minus indicator.

### Inputs / Fields

The refinement textarea uses Paper, Warm Border, the button radius, and the frontmatter padding. It is vertically resizable between a minimum height of (134px) and maximum height of (360px), with type at (14px) and line height (1.7). Its character count sits inside the lower-right corner; the source limit is (300) characters. Errors use the semantic error pair in a rounded inline alert. Loading disables submission and quick-request controls while the existing selection stays visible.

### Navigation and focus

The Paper header has a bottom border. Its desktop menu gap is (40px), reducing to (24px) on small screens. The current link uses semibold text and a two-pixel Toffee underline along the header edge. The three-step form navigation uses thin bottom rules, circular numbers, and Light Toffee completed/current markers.

Every keyboard-focusable control uses an Action Brown outline (2px) with an offset of (4px). Hidden radio and checkbox focus is drawn around the visible parent label. The skip link becomes visible on focus. Route changes focus the page title; that programmatic title focus deliberately has no outline, while control focus remains visible.

### Saving and feedback

The standard save action is a smaller secondary button with a minimum height of (42px), a heart icon, and explicit text. Saving changes the label from `옷장에 담기` to `담았어요`, fills the heart, applies Light Toffee, and updates `aria-pressed`. The compact wardrobe variant uses an icon button with an accessible product-specific label.

Save and remove actions show a fixed Espresso toast with Paper text, an (8px) radius, and a (200ms) `ease-out` entrance from (8px) below. The polite status message remains visible for (3500ms). With `prefers-reduced-motion: reduce`, all animations and transitions are disabled and scrolling uses `auto`; the textual and color feedback remains.

## Do's and Don'ts

### Do:

- **Do** preserve the confirmed calm, sophisticated light-toffee, cream, and espresso mood.
- **Do** reuse the source tokens and single native sans stack for new controls and surfaces.
- **Do** keep product images contained and compact, with concise supporting information.
- **Do** pair selection and saving color changes with checked, pressed, icon, or text feedback.
- **Do** retain visible keyboard focus and the reduced-motion behavior.
- **Do** use the existing responsive thresholds and preserve meaningful content order.

### Don't:

- **Don't** return broad page surfaces to the darker mocha direction the user replaced.
- **Don't** add shadows or lifting hover effects to ordinary cards and buttons.
- **Don't** replace the v3 compositions or confirmed copy as a side effect of styling work.
- **Don't** use color alone to communicate selected or saved state.
- **Don't** remove the visible sample-product disclosures while the frontend uses local demonstration data.
