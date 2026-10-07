---
name: langgraph-engineering
description: Official LangGraph best practices and architectural patterns for building stateful multi-agent workflows, managing TypedDict StateGraphs, Human-in-the-Loop (HITL) persistent checkpoints, conditional routing edges, and tool integration. Use when creating or modifying LangGraph pipelines, agent nodes, or state definitions.
---

# LangGraph Multi-Agent Engineering Best Practices

This skill outlines production engineering patterns for constructing robust, stateful multi-agent pipelines and directed cyclic graphs using **LangGraph** and **LangChain** within Python backend architectures.

## 1. State Machine & TypedDict Definitions

1. **Explicit State Modeling**:
   - Always define the core workflow state (e.g., `TriageAgentState`) using `TypedDict` or `Pydantic` BaseModels.
   - Utilize explicit LangGraph state reducers for collection fields that accumulate historical artifacts across node executions:
     ```python
     from typing import TypedDict, Annotated, List, Dict, Any
     import operator
     from langchain_core.messages import AnyMessage

     class TriageAgentState(TypedDict):
         messages: Annotated[List[AnyMessage], operator.add]
         current_esi_level: int | None
         triage_summary: str
         red_flag_triggered: bool
         audit_logs: Annotated[List[Dict[str, Any]], operator.add]
         next_step: str
     ```

2. **Immutability & Partial Updates**:
   - Nodes must never modify state in-place. Each executing node function must return a dictionary containing ONLY the key-value pairs that need to be appended or updated in the existing state.

## 2. Micro-Node Architecture & Separation of Concerns

Deconstruct massive prompts and complex logic into isolated, single-purpose async micro-nodes within `agents/nodes/`:

- `redflag_detector`: Fast rule-based + minimal LLM screening node designed solely to detect emergent life-threatening patterns and short-circuit normal execution.
- `intake_analyzer`: Evaluates patient dialogue for contradictory statements and extracts structured patient background history.
- `question_engine`: Generates targeted clarification questions (including structured multiple-choice options) when symptom severity is ambiguous.
- `triage_reasoner`: Performs Hybrid RAG queries against medical protocols to determine accurate Emergency Severity Index (ESI 1-5) ratings.
- `summary_creator`: Synthesizes final clinical findings into a structured SBAR (Situation-Background-Assessment-Recommendation) handoff document.

## 3. Deterministic Routing & Conditional Edges

1. **Low-Latency Routing**:
   - Router functions attached to conditional edges (`graph.add_conditional_edges(...)`) must remain deterministic and fast. Do not invoke complex LLM completions inside routing evaluators. Evaluate state flags or simple regex rules directly:
     ```python
     def route_after_intake(state: TriageAgentState) -> str:
         if state.get("red_flag_triggered", False):
             return "emergency_escalate"
         if state.get("current_esi_level") is None:
             return "question_engine"
         return "triage_reasoner"
     ```

## 4. Human-in-the-Loop (HITL) & Persistent Checkpointing

In clinical healthcare systems, AI assistants assist rather than replace certified professionals. Critical clinical decisions require human oversight and validation.

1. **Database Checkpointers**:
   - Attach a persistent database checkpointer (e.g., Postgres checkpointer or Redis/Sqlite memory saver for local development) to your compiled graph to maintain fault-tolerant conversation histories:
     ```python
     from langgraph.checkpoint.postgres import PostgresSaver
     # Attach checkpointer when compiling the graph:
     app = triage_graph.compile(
         checkpointer=postgres_checkpointer,
         interrupt_before=["summary_creator", "queue_pusher"]
     )
     ```
2. **Execution Interrupts**:
   - Use `interrupt_before` or `interrupt_after` checkpoints to pause graph execution just before publishing clinical assessments to nurse workflows or altering official patient health records. The workflow stays suspended until a clinical user approves or modifies the proposed state via REST/WebSocket API endpoints.

## 5. Tool Integration & Fallback Resilience

- Wrap external tool calls (vector searches, patient database lookups, SMS notification emitters) in resilient LangChain `@tool` decorators featuring structured Pydantic input schemas and automated retry mechanics.
- If an LLM reasoning node encounters an API timeout or rate limit, provide explicit programmatic fallbacks to secondary LLM providers (e.g., fallback from Gemini 1.5 Pro to GPT-4o or secondary model tiers) to guarantee clinical workflow uptime.
