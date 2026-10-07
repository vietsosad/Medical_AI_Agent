---
name: medtriage-deepagent-system
description: Implement or audit the MedTriage DeepAgent supervisor, runtime lifecycle, specialist subagents, clinical tools, state recovery, and SSE adapter. Use for changes under src/agents/deepagent_runtime, DeepAgent dependencies/configuration, or migration away from the repository's custom LangGraph StateGraph.
---

# MedTriage DeepAgent System

Treat DeepAgent as the orchestration layer and deterministic clinical tools as
the only authority allowed to alter patient-visible state.

## Workflow

1. Run the emergency reflex before invoking a model.
2. Bind one isolated turn context and expose only prerequisite-gated tools.
3. Let the supervisor or a specialist choose the next allowed tool.
4. Discard free-form model prose; return only verified clinical state.
5. Complete missing required tools in deterministic degraded mode.
6. Persist chat/case artifacts and rebuild hot state from durable messages.
7. Preserve the public REST DTO and SSE phase contract.

Read [references/runtime-contract.md](references/runtime-contract.md) before
changing lifecycle, tool order, state ownership, or event mapping.

## Invariants

- Never reintroduce a custom `StateGraph` as the FastAPI runtime.
- Accept that the `deepagents` package uses LangGraph internally.
- Never give a patient-facing model unrestricted host filesystem or shell access.
- Keep tool outputs small and omit hidden chain-of-thought.
- Mark missing provider/package/tool completion as deterministic degraded mode.
