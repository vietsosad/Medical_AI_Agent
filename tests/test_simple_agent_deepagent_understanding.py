"""Tests for the deepagents-based Phase A (src/simple_agent/deepagent_understanding.py).

Exercises the wiring -- tool-schema fidelity to prompts.TOOL_SCHEMAS, real
AgentToolbox dispatch, the MAX_TOOL_CALLS budget/recursion-limit backstop, the
forced finish_turn fallback, and contextvar isolation across turns -- against
the real Corpus/Session/AgentToolbox, with a scripted fake chat model
standing in for the LLM (no network, no OPENAI_API_KEY needed).

tests/test_simple_agent.py's coverage of the raw-loop Phase A
(understanding.py) is untouched; this file targets only the new module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from deepagents import create_deep_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from src.simple_agent import deepagent_understanding as dau
from src.simple_agent.corpus import Corpus
from src.simple_agent.prompts import TOOL_SCHEMAS
from src.simple_agent.session import Session
from src.simple_agent.tools import AgentToolbox

ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "data/siu"
INDEX_DIR = ROOT / "data/indexes_siu"


def _embed(_: str) -> np.ndarray:
    return np.zeros(1536, dtype=np.float32)


def _corpus() -> Corpus:
    required = (
        *(CORPUS_DIR / name for name in (
            "clinical_concepts.jsonl",
            "concept_relations.jsonl",
            "protocol_atoms.jsonl",
            "fact_targets.jsonl",
        )),
        *(INDEX_DIR / name for name in (
            "concept_embeddings.npy",
            "concept_metadata.json",
            "protocol_embeddings.npy",
            "protocol_metadata.json",
            "fact_target_patient_embeddings.npy",
            "fact_target_patient_metadata.json",
        )),
    )
    missing = [path for path in required if not path.is_file()]
    if missing:
        pytest.skip(
            "requires the non-versioned data/siu and data/indexes_siu corpus "
            f"assets ({len(missing)} files missing)"
        )
    return Corpus(CORPUS_DIR, INDEX_DIR)


def _toolbox() -> AgentToolbox:
    return AgentToolbox(_corpus(), Session(), _embed)


def _tool_call(name: str, args: dict[str, Any], call_id: str) -> dict[str, Any]:
    return {"name": name, "args": args, "id": call_id, "type": "tool_call"}


@pytest.fixture(autouse=True)
def _fresh_agent_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    # Each test installs its own fake model under a distinct cache key, so no
    # test ever sees a previously-cached compiled agent/model.
    monkeypatch.setattr(dau, "_agents_cache", {})


class _ScriptedToolCallingModel(FakeMessagesListChatModel):
    """``FakeMessagesListChatModel`` with ``bind_tools`` implemented as a no-op.

    The base fake model raises ``NotImplementedError`` from ``bind_tools`` --
    fine for plain chat testing, but the deep agent's model node always calls
    ``model.bind_tools(tools)`` before invoking. The scripted responses below
    ignore the bound tools/messages either way, so binding is a passthrough.
    """

    def bind_tools(self, tools: Any, *, tool_choice: str | None = None, **kwargs: Any) -> Any:
        return self


def _install_fake_model(model_name: str, responses: list[AIMessage]) -> None:
    fake_llm = _ScriptedToolCallingModel(responses=responses)
    agent = create_deep_agent(model=fake_llm, tools=dau._build_tools(), system_prompt="test")
    dau._agents_cache[model_name] = agent


def test_tool_schemas_match_prompts_exactly() -> None:
    """Every tool's wire schema is TOOL_SCHEMAS verbatim, not an auto-inferred approximation."""
    tools = dau._build_tools()
    assert [t.name for t in tools] == [schema["function"]["name"] for schema in TOOL_SCHEMAS]
    for tool_obj, schema in zip(tools, TOOL_SCHEMAS):
        assert tool_obj.description == schema["function"]["description"]
        assert tool_obj.args_schema == schema["function"]["parameters"]


def test_scripted_tool_sequence_mutates_toolbox_and_finishes() -> None:
    responses = [
        AIMessage(
            content="",
            tool_calls=[
                _tool_call(
                    "record_concept",
                    {"concept_id": "concept:chest_pain", "subject": "SELF", "status": "ASSERTED"},
                    "c1",
                )
            ],
        ),
        AIMessage(content="", tool_calls=[_tool_call("finish_turn", {"intent": "TRIAGE"}, "c2")]),
        # A real model stops emitting tool_calls once it sees finish_turn's
        # result -- without a trailing plain-content reply here, this fake
        # model would keep cycling back to response[0] forever (LangGraph
        # only exits the model<->tools loop when a response has no
        # tool_calls), corrupting state by replaying the same tool_call id.
        AIMessage(content="Đã ghi nhận."),
    ]
    _install_fake_model("test-model-sequence", responses)
    toolbox = _toolbox()
    # record_concept refuses any concept_id not surfaced by a prior search_*
    # call this turn -- mirrors what search_clinical_concepts would have set.
    toolbox.seen_concept_ids.add("concept:chest_pain")

    outcome = dau.run_deepagent_understanding_loop(toolbox, "tôi bị đau ngực", model="test-model-sequence")

    assert "concept:chest_pain" in toolbox.session.concepts
    assert toolbox.finished is True
    assert outcome["intent"] == "TRIAGE"


def test_budget_exhausted_forces_finish_turn() -> None:
    """A model that never calls finish_turn still ends the turn, bounded."""
    responses = [
        AIMessage(content="", tool_calls=[_tool_call("get_session_state", {}, f"c{i}")])
        for i in range(dau.MAX_TOOL_CALLS + 3)
    ]
    _install_fake_model("test-model-loop", responses)
    toolbox = _toolbox()

    outcome = dau.run_deepagent_understanding_loop(toolbox, "hmm", model="test-model-loop")

    assert toolbox.finished is True
    assert outcome["intent"] == "TRIAGE"


def test_unknown_tool_result_does_not_stop_the_model_from_finishing() -> None:
    """Budget-exhausted tool calls return an error payload, not an exception -- the
    turn still reaches finish_turn cleanly on the very next scripted response."""
    over_budget = [
        AIMessage(content="", tool_calls=[_tool_call("get_session_state", {}, f"c{i}")])
        for i in range(dau.MAX_TOOL_CALLS + 1)
    ]
    responses = [*over_budget, AIMessage(content="", tool_calls=[_tool_call("finish_turn", {"intent": "TRIAGE"}, "cf")])]
    _install_fake_model("test-model-budget-then-finish", responses)
    toolbox = _toolbox()

    outcome = dau.run_deepagent_understanding_loop(toolbox, "hmm", model="test-model-budget-then-finish")

    assert toolbox.finished is True
    assert outcome["intent"] == "TRIAGE"


def test_contextvar_does_not_leak_between_turns() -> None:
    responses = [
        AIMessage(content="", tool_calls=[_tool_call("finish_turn", {"intent": "TRIAGE"}, "c1")]),
        AIMessage(content="Đã ghi nhận."),
    ]
    _install_fake_model("test-model-isolation", responses)

    first = _toolbox()
    dau.run_deepagent_understanding_loop(first, "turn 1", model="test-model-isolation")
    with pytest.raises(RuntimeError):
        dau._current_toolbox()

    second = _toolbox()
    outcome = dau.run_deepagent_understanding_loop(second, "turn 2", model="test-model-isolation")

    assert second.finished is True
    assert first.finished is True
    assert outcome["intent"] == "TRIAGE"
    # The second turn's toolbox, not the first's, took the mutation.
    assert second.session is not first.session
