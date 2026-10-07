# 🧠 MASTER WORKSPACE RULES & AGENT DIRECTIVES (AGENTS.md)
*This is the root Customization Rulefile for all AI Coding Assistants (Antigravity, Cursor, Gemini, Claude) operating within this project repository.*

## 1. PROJECT ARCHITECTURE OVERVIEW
This repository builds a production-grade **Clinical Triage & Medical Assistant Web Application** featuring a tool-gated DeepAgent runtime on FastAPI + PostgreSQL + pgvector RAG and a modern Frontend (Next.js App Router + Tailwind CSS v4 + shadcn/ui). Deep Agents uses LangGraph internally; the repository does not own a custom StateGraph runtime.

---

## 2. 🚨 NEXT.JS 15 WARNING (CRITICAL BREAKING CHANGES)
When writing Frontend code inside `frontend/`:
- **This is NOT older versions of Next.js.** Next.js 15 App Router conventions, caching defaults (fetch requests are no longer cached by default), dynamic routing params (which are now asynchronous Promises: `await params` / `await searchParams`), and server action handling differ from historical training data.
- Rely on modern Next.js 15 standards and check `node_modules/next/dist/docs/` if necessary before inferring historical API structures. Heed all build deprecation warnings.

---

## 3. 🛠️ MANDATORY FRONTEND REFERENCE PROTOCOL (NO EXCEPTIONS)
Whenever the user requests creating, reviewing, debugging, or styling ANY Frontend screen, UI component, page layout, or interactive workflow in `frontend/`, **THE AGENT MUST STRICTLY REFER TO AND ADHERE TO THE FOLLOWING DOCUMENTATION BEFORE WRITING CODE**:

1. **Supreme UI Redesign Constitution (MANDATORY OPERATIONAL SYSTEM)**:  
   👉 Must conform strictly to [UI_REDESIGN_SYSTEM.md](file:///home/viet/Documents/vinAI/P-159/UI_REDESIGN_SYSTEM.md)  
   *(Enforces: **MANDATORY 60-30-10 COLOR SPATIAL RULE, 3 BLUE CLINICAL THEMES (Pristine Day Medical, Deep Slate Night ER, Pediatric & Family Serenity), & SEMANTIC STATUS COLORS (Success Green, Danger Red, Warning Amber, Info Blue for Bright/Light UI) which EVERY AGENT MUST READ BEFORE TOUCHING FRONTEND CODE.** Clarity over beauty. Readability over decoration. Operational efficiency over aesthetics. Cognitive load must be under 3 seconds [Who, What, Urgency, Action]. Strict 8px spacing grid [8, 16, 24, 32...]. Typography min 14-16px for body text and 16-20px for critical medical data [NO tiny labels]. Max 3 primary colors & 1 accent color for status only. No excessive badges, no decorative borders, no nested cards. WCAG AA contrast, Touch targets >= 44px. Every redesign MUST begin with an Audit Report & Rule Validation, targeting QA score >= 95).*
2. **Tech Stack Mandates & Architecture**:  
   👉 Must conform to [frontend-rules.md](file:///home/viet/Documents/vinAI/P-159/.agents/rules/frontend-rules.md)  
   *(Enforces: Next.js 15, TypeScript Strict Mode, Tailwind CSS v4, shadcn/ui + Radix UI, TanStack Query v5 for API cache, Zustand for UI state, React Hook Form + Zod, Motion, Recharts, TanStack Table v8).*
3. **Clinical Core Feature Requirements & Workflows**:  
   👉 Align functional scope with [UI_SCREENS_AND_WORKFLOW_MAP.md](file:///home/viet/Documents/vinAI/P-159/UI_SCREENS_AND_WORKFLOW_MAP.md) and [UI_UX_FUNCTIONAL_GROUPS_AND_ROADMAP.md](file:///home/viet/Documents/vinAI/P-159/UI_UX_FUNCTIONAL_GROUPS_AND_ROADMAP.md).

---

## 3.B 🛠️ MANDATORY BACKEND REFERENCE PROTOCOL (NO EXCEPTIONS)
Whenever the user requests creating, reviewing, debugging, or extending ANY Backend API router, DeepAgent runtime/tool, SQLModel database schema, or Hybrid RAG logic in `src/`, **THE AGENT MUST STRICTLY REFER TO AND ADHERE TO THE FOLLOWING DOCUMENTATION BEFORE WRITING CODE**:

1. **Backend Tech Stack & Architecture Rules**:  
   👉 Must conform to [backend-rules.md](file:///home/viet/Documents/vinAI/P-159/.agents/rules/backend-rules.md)  
   *(Enforces: FastAPI modular routing, SQLModel over SQLAlchemy, Asyncer, tool-gated DeepAgent state updates, pgvector hybrid retrieval, and Pydantic v2 DTOs).*
2. **Clinical Solution Design Blueprint**:  
   👉 Must conform to [TRIAGE_AGENT_SOLUTION_DESIGN.md](file:///home/viet/Documents/vinAI/P-159/TRIAGE_AGENT_SOLUTION_DESIGN.md)  
   *(Enforces: Dual-layer <50ms emergency reflex shielding, diagnosis suppression firewalls, nurse HITL, fail-closed tool gates, and 100% protocol citation provenance).*

---

## 4. 🛠️ MANDATORY AGENT SKILL TRIGGER RULES
When engaging in engineering tasks, the agent must proactively evaluate and integrate guidelines from the project's custom installed skills located in `.agents/skills/`:

### Frontend Skills (UI/Next.js/React):
- **`shadcn-ui`**: Use for open source component modification in `src/components/ui/`, accessible keyboard WAI-ARIA standards, `cn()` utility classname merging, and Zod form patterns.
- **`frontend-design`**: Use to banish default plain colors and simple MVPs. Enforce high-contrast clinical dark palettes (Zinc/Slate), depth lighting, micro-animations, and smooth Framer Motion transitions.
- **`react-best-practices`**: Use to optimize bundle size, eliminate sequential waterfalls (`Promise.all()`, Suspense boundaries), preserve React Server Component boundaries, and prevent redundant re-renders.

### Backend Skills (Python/FastAPI/DeepAgent/RAG):
- **`medtriage-deepagent-system`**: Use for supervisor lifecycle, tools, subagents, state recovery, and SSE adaptation.
- **`medtriage-deepagent-router`**: Use for intent, intake, readiness, clarification, and patient confirmation.
- **`medtriage-rag-evidence`**: Use for retrieval authority, calibration, evidence gates, and citation provenance.
- **`medtriage-clinical-safety`**: Use for emergency reflex, output firewall, ESI/SBAR gates, and nurse HITL.
- **`langgraph-engineering`**: Use only when Deep Agents' internal LangGraph dependency is directly in scope; do not introduce a repository-owned StateGraph runtime.
- **`fastapi-production`**: Use when structuring modular async FastAPI routers, managing real-time WebSocket connection pools for nurse triage feeds, injecting database dependencies (`Depends`), or enforcing strict Pydantic v2 schemas.
- **`clinical-rag-guardrails`**: Use when implementing Hybrid Search (ChromaDB Vector + BM25 keyword retrievers), ensuring 100% protocol citation provenance, structuring JSON tool outputs, or building the mandatory dual-layer emergency reflex (<50ms regex interception) and diagnosis-suppression firewalls.

---

## 5. 🏥 CLINICAL & BACKEND INTEGRATION BOUNDARIES
1. **State Ownership**: Never cache FastAPI backend payload arrays inside Zustand. TanStack Query (`@tanstack/react-query`) is the exclusive owner of remote data, synchronization, and optimistic UI mutations. Zustand exclusively governs client session state (e.g., active step, sidebar collapsible states, temporary emergency flags).
2. **Dual-Layer Medical Safety & Reflex Overlay**:
   - Any UI interacting with triage symptom ingestion must support receiving instantaneous (<50ms) emergency signals via WebSockets or HTTP headers to trigger the Red-Flag Reflex Screen overlay, locking normal chat and presenting emergency calls (`tel:115`).
   - The UI must never display raw technical stack traces or diagnostic hallucinations to patient view screens.
3. **Strict Type Contracts**: Zero tolerance for TypeScript `any`. All payloads exchanged between Next.js frontend and FastAPI backend must have runtime Zod validation schemas matching defined DTOs.
