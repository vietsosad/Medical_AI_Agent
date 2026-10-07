---
name: shadcn-ui
description: Best practices, architecture guidelines, and component conventions for using shadcn/ui with TailwindCSS, Radix UI primitives, and Next.js App Router. Use this skill when generating, modifying, or refactoring React/Next.js UI components, dialogs, forms, buttons, or dashboards.
---

# Shadcn/UI & Radix Component Conventions

This skill guides the design and implementation of modern, accessible, and highly customized frontend web components using the **shadcn/ui** design pattern (Radix UI headless primitives + TailwindCSS + TypeScript).

## 1. Core Architecture Principles

1. **Open & Mutable Source Over Blackbox Packages**:
   - Unlike traditional UI libraries where components are imported from an immutable npm package, shadcn/ui practices **copying and modifying source files** directly into `src/components/ui/`.
   - Always extend components to fit the project's clinical theme and interactive requirements rather than overriding via complex css selectors.
2. **Accessible Headless Primitives (Radix UI)**:
   - Always rely on Radix UI primitives for dialogs, popovers, dropdowns, menus, tabs, and switches to guarantee robust keyboard navigation (Tab, Arrow keys, Escape to close) and WAI-ARIA screen reader support out of the box.
3. **Strict Type-Safety**:
   - All components must export clean TypeScript interfaces. Avoid `any` or loose prop typing.
   - Use React component typing cleanly: `React.ForwardRefExoticComponent` or explicit forwardRef patterns where refs are needed for DOM focus and animations.

## 2. The Universal Classname Merger (`cn` utility)

To prevent Tailwind CSS class collisions and ensure seamless prop overriding, all component classNames MUST be constructed using the `cn()` helper:

```ts
// src/lib/utils.ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### Component Implementation Pattern
```tsx
import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "emergency" | "outline" | "ghost";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-xl font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 disabled:pointer-events-none disabled:opacity-50",
          {
            "bg-gradient-to-r from-cyan-500 to-blue-600 text-white hover:from-cyan-400 hover:to-blue-500 shadow-lg shadow-cyan-500/20": variant === "primary",
            "bg-rose-600 text-white hover:bg-rose-500 shadow-[0_0_20px_rgba(244,63,94,0.4)] animate-pulse": variant === "emergency",
            "border border-zinc-800 bg-transparent hover:bg-zinc-800 text-zinc-200": variant === "outline",
            "hover:bg-zinc-800/50 text-zinc-300 hover:text-white": variant === "ghost",
          },
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
export { Button };
```

## 3. Tailwind Design Tokens & Theme Variable Mapping

Maintain semantic CSS variables in `globals.css` / `index.css` mapped to Tailwind classes rather than hardcoding ad-hoc hex codes across views:

- `bg-background`: Main container background (`bg-zinc-950` in dark mode).
- `text-foreground`: Primary legible typography (`text-zinc-100`).
- `border-border`: Subtle panel outlines (`border-zinc-800/60`).
- `bg-muted`: Secondary cards or disabled states (`bg-zinc-900/50`).
- `text-destructive`: Error logs or clinical emergency red flags (`text-rose-500`).

## 4. Standard Form & Validation Pattern (React Hook Form + Zod)

When creating user inputs, patient questionnaires, or clinical override forms, use **React Hook Form** coupled with **Zod schema validation**:

```tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";

const overrideSchema = z.object({
  esi_level: z.number().min(1).max(5),
  justification: z.string().min(10, "Lý do lâm sàng bắt buộc dài từ 10 ký tự trở lên."),
});

type OverrideFormValues = z.infer<typeof overrideSchema>;
```

## 5. UI Hygiene & Clinical Operational Best Practices (UI_REDESIGN_SYSTEM)

- **Strict 8px Spacing Grid**: All spacing values must conform strictly to multiples of 8px (`p-2`, `p-4`, `p-6`, `gap-2`, `gap-4`). Eliminate arbitrary values like `p-2.5`, `py-1.5`, or `m-3`.
- **Mandatory Touch Targets (>= 44px)**: To satisfy WCAG AA accessibility standards in clinical tablet environments, all interactive primitives (buttons, switches, dropdown triggers, questionnaire choices) must maintain a minimum bounding box of **44px × 44px (`min-h-[44px] min-w-[44px]`)**.
- **No Nested Cards (Zero Visual Noise)**: Never wrap child elements in redundant bordered containers inside an outer card component. Keep visual hierarchy strictly flat and readable under 3 seconds.
- **Icon Integration (Lucide Only)**: Pair shadcn components exclusively with `lucide-react` vector icons. **Never put text emojis (🛡️, 🚨, ⚡) inside buttons or UI labels.** Standardize icon sizes (`w-4 h-4` for inline labels, `w-5 h-5` for primary triggers).
- **Zero Flash of Unstyled Content**: Use skeleton loaders (`animate-pulse bg-slate-200 rounded-xl`) with exact matching dimensions for lazy-loaded clinical telemetry.

