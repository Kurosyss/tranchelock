# TRANCHELOCK FRONTEND DESIGN SYSTEM SPECIFICATION

This document establishes the permanent frontend design-system rules for TrancheLock.
Any AI assistant or developer modifying frontend code must follow these rules without exception.
DO NOT invent arbitrary styles, dark-mode crypto templates, neon glow borders, or generic card-grid dashboards.

---

## 1. System Philosophy: An Exercise in Subtraction

The Geist system is an exercise in subtraction:
* The page is a near-white sheet (`--canvas: #fafafa`) carrying near-black ink (`--ink: #171717`), and almost nothing else competes.
* Headings, body copy, primary buttons, and the thin 1px borders that define cards all draw from the same ink-and-grey ladder.
* The only place color is allowed to exist as ambient bloom is the hero, where a soft multi-stop **mesh gradient** (cyan, blue, violet, magenta, amber) blooms behind or beside the headline. Everywhere else: absolute restraint.
* Surfaces barely lift: cards are pure white (`--canvas-elevated: #ffffff`) on the `#fafafa` canvas, separated by a 1px hairline (`--hairline: #ebebeb`) and, at most, a whisper-soft layered shadow (`0px 1px 1px rgba(0,0,0,0.04)`).
* The page reads like documentation that happens to be introducing an engineered protocol — exact, crisp, and confident.

---

## 2. Palette & Color System (Exact DESIGN.md Tokens)

### 2.1 Surfaces & Canvas
* **Canvas** (`--canvas`): `#fafafa` — default page background sheet.
* **Canvas Elevated** (`--canvas-elevated`): `#ffffff` — pure white for cards, inputs, buttons, and code blocks.
* **Hairline Soft Surface** (`--hairline-soft`): `#f2f2f2` — subtle alternating panels, code block headers, inset wells.

### 2.2 Text Ladder
* **Ink** (`--ink` / `--primary`): `#171717` — primary headings, high-emphasis text, logo wordmark, primary button fill.
* **Body** (`--body`): `#4d4d4d` — standard paragraph and secondary copy, nav links.
* **Mute** (`--mute`): `#8f8f8f` — lower-emphasis captions, metadata, technical labels.
* **Faint** (`--faint`): `#a1a1a1` — lowest tier, placeholders, disabled labels.

### 2.3 Borders & Dividers
* **Hairline** (`--hairline`): `#ebebeb` — 1px solid border on every card, input, table row, and divider.

### 2.4 Accents & Semantic Signals
* **Vercel Blue / Link** (`--link`): `#0070f3` (press: `#0761d1`, soft: `#d3e5ff`) — inline links, focus rings, primary active signals.
* **Error / Rejection** (`--error`): `#ee0000` (deep: `#c50000`) — failed tests, rejected signatures, invalid states.
* **Warning** (`--warning`): `#f5a623` (soft: `#ffefcf`, deep: `#ab570a`) — timelocks, pending states.
* **Success / Release**: `#10b981` (onchain settlement / test pass) / `#0070f3` (system positive).
* **Hero Mesh Gradient Stops**:
  * Cyan (`#50e3c2`), Blue (`#007cf0`), Violet (`#7928ca`), Magenta (`#eb367f`), Amber (`#f9cb28`).
  * Confined strictly to the hero background. No gradients anywhere else.

---

## 3. Typography Hierarchy & Tokens

Typography does the heavy lifting. All prose and UI uses **Geist Sans**. Technical eyebrows, addresses, hashes, and code use **Geist Mono**. Exceptional high-value moments use **Geist Pixel**.

### 3.1 Systematic Typography Scale (DESIGN.md Mapping)

| Token | Class | Size | Weight | Line Height | Tracking | Use |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`display-xl`** | `.type-display-xl` | 48px | 600 | 48px | `-2.4px` (`-0.05em`) | Hero headlines |
| **`heading-lg`** | `.type-heading-lg` | 32px | 600 | 40px | `-1.28px` (`-0.04em`) | Major section headings |
| **`heading-md`** | `.type-heading-md` | 20px | 600 | 28px | `-0.4px` (`-0.02em`) | Sub-section headings & card titles |
| **`label-sm`** | `.type-label-sm` | 14px | 500 | 20px | `-0.28px` (`-0.02em`) | Strong labels, nav emphasis, table headers |
| **`mono-eyebrow`** | `.type-mono-eyebrow`| 12px | 500 | 16px | `0` | Uppercase Geist Mono section eyebrows |
| **`body-lg`** | `.type-body-lg` | 16px | 400 | 24px | `0` | Lead paragraphs, hero descriptions |
| **`body-md`** | `.type-body-md` | 14px | 400 | 20px | `0` | Default body copy, nav links, table cells |
| **`body-sm`** | `.type-body-sm` | 12px | 400 | 16px | `0` | Captions, footnotes, metadata |
| **`button-lg`** | `.type-button-lg` | 16px | 500 | 20px | `0` | Marketing pill button labels |
| **`button-md`** | `.type-button-md` | 14px | 500 | 20px | `0` | Nav and in-app button labels |
| **`code`** | `.type-code` | 14px | 400 | 20px | `0` | Code blocks, inline code (Geist Mono) |

### 3.2 Principles
* Display type is defined by tight negative tracking — the larger the heading, the tighter.
* Weight is binary: 600 for headings, 500 for buttons/labels, 400 for everything else.
* Small text is deliberate: never reduce all small text to identical 10px uppercase mono. Use `body-sm` (Geist Sans) for captions and `mono-eyebrow` for section eyebrows.

### 3.3 Geist Pixel Discipline (High-Value Moments Only)
Geist Pixel is NOT a generic body or label font. Use Pixel only for a small number of exceptional moments where digital state transition is communicated:
* **`GeistPixelSquare` (`.pixel-square`)**: Milestone numbers (`[01]`, `[02]`), completed state markers.
* **`GeistPixelCircle` (`.pixel-circle`)**: Capital values (`+$50.00`, `$100.00 LOCKED`).
* **`GeistPixelGrid` (`.pixel-grid`)**: Verified state, attestation badge (`VERIFIED`, `SETTLED`).
* **`GeistPixelTriangle` (`.pixel-triangle`)**: Active executing transition.
* **`GeistPixelLine` (`.pixel-line`)**: Container telemetry isolation tag (`ZERO-NET`).

---

## 4. Spacing, Layout & Depth

### 4.1 Spacing Scale (4px Base)
* `xxs`: 4px · `xs`: 8px · `sm`: 12px · `md`: 16px · `lg`: 24px · `xl`: 32px · `2xl`: 40px · `3xl`: 64px · `4xl`: 96px · `section`: 128px.
* Section padding runs `96px`–`128px` (`py-24` to `py-32`). Card interiors sit at `24px`–`32px` (`p-6` to `p-8`).

### 4.2 Layout Widths
* **Page Container**: `1200px` (`max-w-[1200px] mx-auto px-4 sm:px-6`).
* **Reading Width (Docs/Prose)**: `680px`–`768px` (`max-w-[768px]`).
* **Feature Bands**: Full width with centered max-w-[1200px] container.

### 4.3 Elevation & Depth
* **Level 0 (Flat)**: 1px hairline (`#ebebeb`), no shadow. Default for cards, dividers, inputs.
* **Level 1 (Whisper)**: Border + `0px 1px 1px rgba(0,0,0,0.04)` micro-shadow.
* **Level 2 (Floating)**: Layered soft shadow (`0px 2px 2px rgba(0,0,0,0.03)` + `0px 8px 16px -4px rgba(0,0,0,0.06)`) + 1px hairline.

---

## 5. Component Proportions & Geometry

### 5.1 Bimodal Button Hierarchy
* **Marketing CTAs**: Fully rounded black pills (`rounded-[100px]`, `px-5 py-2.5`, bg `#171717`, text `#ffffff`). Secondary variant: white pill with `#171717` text and `#ebebeb` border.
* **Nav & In-App Controls**: Tight 6px square (`rounded-[6px]`, `px-3 py-1.5`, h-8, text-xs/14px).
* **Category Tabs**: Pill shape (`rounded-[64px]`, `px-4 py-1.5`).

### 5.2 Cards & Containers
* Standard feature card: `#ffffff` surface, 1px `#ebebeb` hairline border, `rounded-[12px]`, `padding: 24px`.
* Code block: `#ffffff` or `#f2f2f2` surface, 1px `#ebebeb` hairline, `rounded-[12px]`, `padding: 16px`, Geist Mono.
* Inputs: `#ffffff` surface, 1px `#ebebeb` hairline, `rounded-[6px]`, `px-3 py-2`.

---

## 6. Prohibited Practices (Anti-Patterns)
* ❌ DO NOT use black canvas backgrounds with neon green/violet glowing borders.
* ❌ DO NOT repeat identical 3-column card grids section after section.
* ❌ DO NOT use ASCII terminal art diagrams.
* ❌ DO NOT make all small text uppercase 10px monospace.
* ❌ DO NOT overuse Geist Pixel across ordinary paragraphs or labels.
* ❌ DO NOT use arbitrary colors outside the ink ladder and defined semantic signals.
