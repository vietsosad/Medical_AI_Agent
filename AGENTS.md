# Codex Workspace Instructions

This file is the automatically discovered Codex entry point for this repository.
The `.agents/` directory is the canonical source for the project's detailed
policies, engineering rules, skills, and workflows. Do not duplicate or move
those files solely for Codex compatibility.

## Required pre-code protocol

Before creating, modifying, reviewing, debugging, or running code-related
commands, read `.agents/AGENTS.md` in full and apply it as the project's master
instruction set. Then identify the work area and read the required sources
below before taking an implementation action.

### Frontend work (`frontend/`)

Read these sources before touching frontend code:

1. `UI_REDESIGN_SYSTEM.md`
2. `.agents/rules/frontend-rules.md`
3. `UI_SCREENS_AND_WORKFLOW_MAP.md` and
   `UI_UX_FUNCTIONAL_GROUPS_AND_ROADMAP.md` when the requested feature affects
   product behavior or user flow.

Use the relevant auto-discovered skills from `.agents/skills/`, especially
`frontend-design`, `shadcn-ui`, `react-best-practices`, and the applicable
Tailwind or design-system skills. Preserve Next.js 15 conventions and the
nested `frontend/AGENTS.md` guidance.

### Backend work (`src/`)

Read these sources before touching backend code:

1. `.agents/rules/backend-rules.md`
2. `TRIAGE_AGENT_SOLUTION_DESIGN.md`

Use the relevant auto-discovered skills from `.agents/skills/`, especially
`fastapi-production`, `clinical-rag-guardrails`, and the four
`medtriage-deepagent-*`/`medtriage-*-safety` skills. Use
`langgraph-engineering` only for LangGraph internals exposed by Deep Agents; do
not introduce a repository-owned StateGraph runtime.
Treat clinical safety, provenance, and HITL requirements as non-negotiable.

### Workflows and logging

Read `.agents/rules/ai-log-hook.md` and `.agents/workflows/log.md` before any
action that concerns AI-usage logging or Git hooks. Codex logging is already
automated through `.codex/hooks.json`; do not run manual logging scripts or
edit `.ai-log/` during normal work.

## Skill discovery

Codex automatically discovers every valid skill under `.agents/skills/` at the
repository root. Select and read each matching skill's `SKILL.md` completely
before using that skill. Keep project skills in this location so they are
available to every Codex session launched anywhere in this repository.

## Instruction precedence

This root instruction applies to the whole repository. More specific nested
`AGENTS.md` files, including `frontend/AGENTS.md`, add to and override it for
their own subtrees.
