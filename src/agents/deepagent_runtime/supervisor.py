"""Tool-gated DeepAgent supervisor for the MedTriage clinical runtime."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel

from src.agents.deepagent_runtime.events import phase_completed
from src.agents.deepagent_runtime.schemas import DeepAgentStateSnapshot
from src.agents.deepagent_runtime.state_store import DeepAgentSessionStore
from src.agents.deepagent_runtime.subagents import build_subagent_specs
from src.agents.deepagent_runtime.tools import (
    TurnContext,
    bind_turn_context,
    build_clinical_tools,
    reset_turn_context,
    run_reflex_screen,
    run_remaining_required_tools,
)
from src.config import get_settings
from src.services.llm_provider import get_deepagent_llm

logger = logging.getLogger(__name__)

# How a finished turn is labelled for audit. A confirmed emergency, a
# precautionary fallback and an unresolved-context clarification must stay
# distinguishable after the fact.
_RED_FLAG_EXECUTION_MODES = {
    "CONFIRMED": "EMERGENCY_CONFIRMED",
    "SAFETY_FALLBACK": "EMERGENCY_SAFETY_FALLBACK",
    "UNCERTAIN": "SAFETY_CLARIFICATION",
}


def _resolve_execution_mode(state: dict[str, Any], fallback: str) -> str:
    status = str(state.get("red_flag_status") or "")
    if state.get("emergency_detection_source") == "SEMANTIC_LLM":
        return "EMERGENCY_SEMANTIC"
    resolved = _RED_FLAG_EXECUTION_MODES.get(status)
    if resolved is not None:
        return resolved
    # Defensive: an escalating turn must never be audited as a routine one,
    # even if a caller produced state without the lifecycle field.
    if state.get("is_red_flag"):
        return "EMERGENCY_CONFIRMED"
    return fallback

SUPERVISOR_PROMPT = """
You are the MedTriage orchestration supervisor. You do not diagnose, prescribe,
assign ESI, write SBAR, or answer the patient in free text. The application only
uses state produced by deterministic clinical tools; your prose is discarded.

The deterministic emergency reflex already ran before you were invoked. Advance
exactly one patient turn by calling tools in the order permitted by each result:
1. assess_contextual_emergency to understand combined severe signs
2. classify_request only when the semantic assessment did not escalate
3. update_intake when the request is a triage intake or follow-up
4. retrieve_clinical_evidence only after confirmed readiness
5. reason_and_prepare_handoff only when the evidence gate authorizes it
6. verify_clinical_output exactly once before stopping

You may delegate to the matching specialist subagent. Never retry a rejected
tool, never bypass a prerequisite, never use filesystem content as clinical
evidence, and never turn MIETIC case examples into validated protocols.
""".strip()

_RUNTIME_SKILL_NAMES = (
    "medtriage-deepagent-system",
    "medtriage-deepagent-router",
    "medtriage-rag-evidence",
    "medtriage-clinical-safety",
)


class MedTriageDeepAgentSupervisor:
    """Own DeepAgent construction, execution, event adaptation, and hot state."""

    def __init__(self) -> None:
        self._store = DeepAgentSessionStore()
        self._agent: Any | None = None
        self._agent_lock = asyncio.Lock()
        self._skill_files: dict[str, Any] | None = None

    async def _build_agent(self) -> Any | None:
        settings = get_settings()
        if not settings.deepagent_runtime_enabled:
            return None
        model = get_deepagent_llm()
        if not isinstance(model, BaseChatModel):
            return None
        try:
            from deepagents import create_deep_agent
        except ImportError:
            logger.warning(
                "deepagents is not installed; using deterministic degraded mode"
            )
            return None

        tools = build_clinical_tools()
        return create_deep_agent(
            model=model,
            tools=tools,
            system_prompt=SUPERVISOR_PROMPT,
            subagents=build_subagent_specs(tools),
            skills=["/skills/"],
            name="medtriage-deepagent-supervisor",
        )

    async def _get_agent(self) -> Any | None:
        if self._agent is not None:
            return self._agent
        async with self._agent_lock:
            if self._agent is None:
                self._agent = await self._build_agent()
        return self._agent

    def _load_skill_files(self) -> dict[str, Any]:
        if self._skill_files is not None:
            return self._skill_files
        try:
            from deepagents.backends.utils import create_file_data
        except ImportError:
            self._skill_files = {}
            return self._skill_files

        repo_root = Path(__file__).resolve().parents[3]
        skills_root = repo_root / ".agents" / "skills"
        files: dict[str, Any] = {}
        for skill_name in _RUNTIME_SKILL_NAMES:
            skill_root = skills_root / skill_name
            if not skill_root.exists():
                continue
            for source in skill_root.rglob("*"):
                if not source.is_file() or source.name == "openai.yaml":
                    continue
                relative = source.relative_to(skill_root).as_posix()
                virtual_path = f"/skills/{skill_name}/{relative}"
                files[virtual_path] = create_file_data(
                    source.read_text(encoding="utf-8")
                )
        self._skill_files = files
        return files

    async def _execute_context(
        self,
        context: TurnContext,
        session_id: str,
    ) -> dict[str, Any]:
        # A deterministic reflex match owns a monotonic emergency lock before
        # any orchestration model is constructed. The contextual tool still
        # runs in the bounded completion path to attach semantic observations,
        # but it cannot clear the lock or resume intake.
        model_called_tools: list[str] = []
        reflex_candidate = await run_reflex_screen(context)
        deterministic_reflex_locked = bool(
            context.state.get("is_red_flag")
            and context.state.get("red_flag_status") == "CONFIRMED"
            and context.state.get("emergency_detection_source")
            == "DETERMINISTIC_REFLEX"
        )
        if reflex_candidate or deterministic_reflex_locked:
            execution_mode = (
                "EMERGENCY_CONFIRMED"
                if deterministic_reflex_locked
                else "REFLEX_CANDIDATE"
            )
            await run_remaining_required_tools(context)
        else:
            execution_mode = "DEEPAGENT"
            agent = await self._get_agent()
            agent_completed_gate = False
            if agent is not None:
                token = bind_turn_context(context)
                try:
                    await agent.ainvoke(
                        {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": (
                                        "Advance the active MedTriage turn using only the "
                                        "permitted clinical tools. Finish with "
                                        "verify_clinical_output."
                                    ),
                                }
                            ],
                            "files": self._load_skill_files(),
                        },
                        config={
                            "configurable": {"thread_id": session_id},
                            "recursion_limit": (
                                get_settings().deepagent_max_tool_calls_per_turn
                                * 2
                                + 4
                            ),
                        },
                    )
                    agent_completed_gate = (
                        "verify_clinical_output" in context.called_tools
                    )
                except Exception as exc:
                    logger.warning(
                        "DeepAgent turn degraded to deterministic tools: %s",
                        type(exc).__name__,
                    )
                finally:
                    reset_turn_context(token)
            model_called_tools = sorted(context.called_tools)
            if not agent_completed_gate:
                execution_mode = "DETERMINISTIC_DEGRADED"
            await run_remaining_required_tools(context)

        execution_mode = _resolve_execution_mode(context.state, execution_mode)
        metadata = dict(context.state.get("metadata") or {})
        metadata.update(
            {
                "agent_runtime": "deepagents",
                "execution_mode": execution_mode,
                "tool_call_count": len(context.audit),
                # Which phases the model chose, and which the runtime had to
                # complete for it. Without this split an audit cannot tell an
                # agent that orchestrated its own turn from one that was driven
                # end to end by the deterministic fallback.
                "model_selected_tools": model_called_tools,
                "deterministically_completed_tools": sorted(
                    context.called_tools.difference(model_called_tools)
                ),
            }
        )
        context.state["metadata"] = metadata
        await self._store.save(
            session_id,
            context.state,
            execution_mode=execution_mode,
            tool_audit=context.audit,
        )
        return context.state

    async def run_start(
        self,
        incoming_state: dict[str, Any],
        *,
        session_id: str,
    ) -> dict[str, Any]:
        async with self._store.serialize_turn(session_id):
            state = await self._store.prepare_turn(session_id, incoming_state)
            return await self._execute_context(TurnContext(state), session_id)

    async def stream_turn(
        self,
        incoming_state: dict[str, Any],
        *,
        session_id: str,
    ) -> AsyncIterator[dict[str, Any]]:
        async with self._store.serialize_turn(session_id):
            state = await self._store.prepare_turn(session_id, incoming_state)
            queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
            context = TurnContext(state, queue)
            task = asyncio.create_task(self._execute_context(context, session_id))
            try:
                while True:
                    if task.done() and queue.empty():
                        break
                    queue_task = asyncio.create_task(queue.get())
                    done, _ = await asyncio.wait(
                        {queue_task, task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    if queue_task in done:
                        yield queue_task.result()
                    else:
                        queue_task.cancel()
                result = await task
                yield phase_completed("DeepAgentSupervisor", result).as_dict()
            finally:
                if not task.done():
                    task.cancel()

    async def get_session_state(
        self,
        session_id: str,
    ) -> DeepAgentStateSnapshot:
        session = await self._store.get(session_id)
        return DeepAgentStateSnapshot(
            values=session.clinical_state if session else {}
        )

    async def reset(self) -> None:
        await self._store.clear()
        self._agent = None
        self._skill_files = None


_runtime = MedTriageDeepAgentSupervisor()


def get_deepagent_runtime() -> MedTriageDeepAgentSupervisor:
    return _runtime


async def configure_deepagent_runtime() -> None:
    """Prebuild the runtime when a provider is available."""
    await _runtime._get_agent()


async def reset_deepagent_runtime() -> None:
    await _runtime.reset()
