---
name: frontend-design
description: Operational clinical visual engineering rules from UI_REDESIGN_SYSTEM.md to maximize Readability, Scanability, Usability, Accessibility, and Cognitive Load Reduction (< 3 seconds rule). Trigger when building web interfaces, designing dashboards, questionnaires, or reviewing frontend components against clinical quality standards.
---

# Supreme Clinical Frontend Engineering & UI Redesign System

This skill operationalizes the master mandates from `UI_REDESIGN_SYSTEM.md`. In a high-stakes clinical AI environment, our job is **NOT to make the UI prettier**. Our job is to maximize Readability, Scanability, Operational Efficiency, and Cognitive Load Reduction.

## 1. Core Global Design Principles (The Six Commandments)
1. **Clarity over beauty.**
2. **Readability over decoration.**
3. **Efficiency over aesthetics.**
4. **Hierarchy over density.**
5. **Consistency over creativity.**
6. **Minimalism over visual noise.**

> **The 3-Second Rule**: The UI must be completely understandable in less than 3 seconds. The user must instantaneously grasp: Who, What, How Urgent, and What Action. Remove anything that does not directly answer these four foundational questions.

## 2. Strict Typographic Scale & Zero Tiny Labels
- **Maximum Limits**: Maximum 2 font families, maximum 3 font sizes inside a single card, maximum 2 font weights.
- **Body Text Standard**: Must be **14-16px minimum (`text-sm` or `text-base`)**. Never use tiny unreadable text (`text-[9px]`, `text-[10px]`, `text-[11px]`).
- **Critical Medical Data**: Patient names, ESI Triage levels, SLA Countdown timers, and Chief Complaints must be prominent: **16-20px minimum (`text-base font-bold` or `text-lg / text-xl font-black`)**. Must be legible from across a nurse station.
- **Vector Iconography Exclusive**: **ABSOLUTELY NO TEXT-BASED EMOJIS OR UNICODE SYMBOLS IN UI** (e.g., no 🛡️, 🚨, 🔓, ⚡, 🔥 in buttons, labels, or badges). Always instantiate precision SVG vector components (`lucide-react`) with standard stroke sizing (`stroke-[2.5]`).

## 3. Strict 8px Spacing Grid & Whitespace Mastery
- **Mandatory Grid Values**: Use an exact **8px spacing grid**: `8px (p-2/gap-2)`, `16px (p-4/gap-4)`, `24px (p-6/gap-6)`, `32px (p-8/gap-8)`, `40px (p-10)`, `48px (p-12)`.
- **No Arbitrary Spacing**: Eradicate random micro-paddings (`p-2.5`, `p-3.5`, `py-1.5`, `my-3`). Every component must breathe.
- **Whitespace is Mandatory**: Whitespace is NOT empty space. Whitespace improves speed of comprehension and cuts cognitive fatigue.

## 4. Card & Dashboard Engineering Rules (Zero Nested Clutter)
- **Flat Card Architecture**: Each medical card must contain precisely: Primary Information -> Secondary Information -> **Single Primary CTA**. Nothing else.
- **Prohibitions**: Avoid excessive status badges. **Avoid nested cards** (never draw bordered boxes inside another card). Avoid decorative colored borders or gradients that do not signal clinical status.
- **Medical Triage Priority**: ESI 1 (Resuscitation) must always be sorted first and prominent. Critical patients must be visually pinned. Medical telemetry and patient identities must precede any interactive controls.

## 5. Color as Functional Intelligence Only
- **Palettes**: Maximum 3 primary colors, maximum 1 accent color.
- **Never use color for decoration**: Color exists exclusively to signal Status, Priority, Warning, or Action:
  - **Critical (ESI 1 / Red-Flag)**: Rose / Red (`bg-rose-50 border-rose-600 text-rose-950`).
  - **Warning (ESI 2 / SLA Timeout)**: Amber / Orange (`bg-amber-50 border-amber-500 text-amber-950`).
  - **Normal / Less Urgent (ESI 4-5)**: Calming Emerald (`bg-emerald-50 border-emerald-500 text-emerald-950`).
  - **Information / SBAR Summary**: Sky / Indigo (`bg-sky-50 border-sky-400 text-sky-950`).

## 6. Accessibility & WAI-ARIA Standards (WCAG AA)
- **Touch Target Sizing**: All interactive buttons, choice questionnaires, tabs, and navigation anchors must be at least **44px × 44px (`min-h-[44px] min-w-[44px]`)** to ensure seamless operation on medical tablet touchscreens.
- **Contrast & Focus**: Strict compliance with WCAG AA contrast ratio (>= 4.5:1). Every interactive control must display an explicit focus state (`focus-visible:ring-2 focus-visible:ring-sky-600 focus-visible:ring-offset-2`).
- **Live Alerts**: Emergency red-flag overlays and ESI 1 notification sirens must incorporate `role="alert"` and `aria-live="assertive"`.
