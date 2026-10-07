from __future__ import annotations

from typing import Any

import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ScriptedToolModel(BaseChatModel):
    """Deterministic tool-calling model used without provider/network access."""

    model_name: str = "scripted-tool-model"

    @property
    def _llm_type(self) -> str:
        return "scripted-tool-model"

    def bind_tools(
        self,
        tools: Any,
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ) -> ScriptedToolModel:
        return self

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        completed = [
            message.name
            for message in messages
            if isinstance(message, ToolMessage)
        ]
        if "assess_contextual_emergency" not in completed:
            message = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "assess_contextual_emergency",
                        "args": {},
                        "id": "call-emergency-context",
                        "type": "tool_call",
                    }
                ],
            )
        elif "classify_request" not in completed:
            message = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "classify_request",
                        "args": {},
                        "id": "call-classify",
                        "type": "tool_call",
                    }
                ],
            )
        elif "verify_clinical_output" not in completed:
            message = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "verify_clinical_output",
                        "args": {},
                        "id": "call-verify",
                        "type": "tool_call",
                    }
                ],
            )
        else:
            message = AIMessage(content="done")
        return ChatResult(generations=[ChatGeneration(message=message)])


@pytest.mark.asyncio
async def test_real_deepagent_harness_executes_gated_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("deepagents")
    from src.agents.deepagent_runtime.supervisor import (
        MedTriageDeepAgentSupervisor,
    )

    monkeypatch.setattr(
        "src.agents.deepagent_runtime.supervisor.get_deepagent_llm",
        lambda: ScriptedToolModel(),
    )
    from src.services.llm_provider import MockClinicalAI

    monkeypatch.setattr(
        "src.agents.nodes.contextual_emergency_detector.get_deepagent_llm",
        lambda: MockClinicalAI(),
    )
    runtime = MedTriageDeepAgentSupervisor()

    result = await runtime.run_start(
        {"query": "Hello"},
        session_id="scripted-deepagent-harness",
    )

    assert result["intent"] == "GREETING_HELP"
    assert result["decision_status"] == "NOT_APPLICABLE"
    assert result["metadata"]["execution_mode"] == "DEEPAGENT"
    assert result["metadata"]["tool_call_count"] >= 5
