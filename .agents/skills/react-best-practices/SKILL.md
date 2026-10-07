---
name: react-best-practices
description: React and Next.js 14+ performance optimization and architectural guidelines from Vercel Engineering. Trigger when writing, reviewing, or refactoring React components, Next.js App Router pages, server actions, client data fetching, bundle size optimization, or fixing re-renders and waterfalls.
---

# Vercel React & Next.js Best Practices

Comprehensive engineering guidelines and performance optimization patterns for modern React and Next.js applications, inspired by Vercel Engineering standards. Apply these rules when generating, reviewing, or refactoring application code.

## 1. Eliminating Waterfalls (CRITICAL PRIORITY)

Sequential network or computational blockages ("waterfalls") destroy application loading speeds and perceived performance.

- `async-cheap-condition-before-await`: Evaluate fast, synchronous boolean checks before awaiting database, API calls, or LLM reasoning.
- `async-defer-await`: Move await statements inside conditional branches where the fetched value is actually evaluated or utilized.
- `async-parallel`: Always use `Promise.all()` when executing independent async operations (e.g., querying user profile and retrieving RAG documents concurrently).
- `async-suspense-boundaries`: Wrap streaming UI blocks (such as AI chat generation or heavy clinical telemetry graphs) in `<Suspense fallback={<SkeletonLoader />}>` to unlock non-blocking page renders.
- `async-api-routes`: In FastAPI or Next.js Route Handlers, initiate promise execution early and await as late as possible before response serialization.

## 2. Bundle Size & Import Optimization (CRITICAL PRIORITY)

Keep initial JavaScript payload light to achieve near-instant interaction times (FCP & INP optimization).

- `bundle-barrel-imports`: Avoid importing from massive barrel index files if they break tree-shattering. Import directly from specific submodule paths when necessary.
- `bundle-dynamic-imports`: Use `next/dynamic` or `React.lazy()` for massive interactive charting engines, mapping tools (ER hospital location maps), or complex editors that are hidden by default:
  ```tsx
  import dynamic from 'next/dynamic';
  const EmergencyMapModal = dynamic(() => import('@/components/EmergencyMapModal'), {
    loading: () => <MapSkeleton />,
    ssr: false,
  });
  ```
- `bundle-defer-third-party`: Load optional tracking, analytics, or logging libraries post-hydration using Next Script component (`strategy="lazyOnload"`).

## 3. Server-Side Performance & React Server Components (HIGH PRIORITY)

Next.js App Router utilizes Server Components by default. Maximize server performance and maintain strict boundary separation.

- `server-first-by-default`: Never insert `'use client'` on top-level layout or architectural wrapper files unless direct browser APIs or interactive React hooks (`useState`, `useEffect`, onClick event binding) are explicitly required.
- `server-push-client-leaves`: Push client interactivity to the leaf nodes of your component tree. An interactive vote button or checkbox should be its own minimal Client Component wrapped inside a larger Server Component page.
- `server-cache-react`: Leverage `React.cache()` to deduplicate identical data queries across distinct React Server Components rendering within a single HTTP request lifecycle.
- `server-dedup-props`: Avoid passing large, unneeded serializable object blobs as props from Server Components down to Client Components; pass only essential primitive fields or light DTOs.

## 4. Client-Side State & Re-render Optimization (MEDIUM-HIGH PRIORITY)

- `rerender-referential-equality`: Apply `useMemo` and `useCallback` when passing callback props to heavily complex child components or when computing heavy transformations (e.g., sorting 1,000 hospital queue cards). Do not over-memoize simple primitive components.
- `rerender-stable-keys`: Always provide robust, unique database IDs (UUIDs) for `key` props inside array `.map()` loops. NEVER use array indices as keys in dynamic or reorderable lists (like Kanban triage queues or live messages).
- `client-optimistic-updates`: Use optimistic UX patterns (`useOptimistic` or TanStack Query / SWR optimistic cache updates) so that HITL actions (like clicking "Approve SBAR") register visually in <50ms without waiting for round-trip DB confirmations.

## 5. Accessibility & SEO Essentials (CORE REQUIREMENT)

- `seo-semantic-tags`: Construct interfaces using HTML5 semantic tags (`<header>`, `<main>`, `<aside>`, `<nav>`, `<section>`).
- `a11y-unique-ids`: Assign unique, descriptive IDs and standard WAI-ARIA labels (`aria-label`, `role="alert"`) to interactive elements, alarm banners, and medical option cards to empower screen readers and seamless automated browser testing.
