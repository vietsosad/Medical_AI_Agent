"""Assemble the context for a turn under a budget, without losing what matters.

Sending the whole transcript every turn costs tokens and latency, and buries the
clinically important lines among acknowledgements. Sending too little loses the
thread. This module decides what goes in, in a fixed priority order, and drops
from the bottom when the budget runs out.

The ordering is the safety property. Safety constraints, the current message and
canonical clinical state are non-negotiable and are never dropped. Important
clinical events rank above ordinary recent conversation, so a red-flag candidate
or a correction from turn 3 survives while chit-chat from turn 19 does not.
If the budget cannot fit even the non-negotiable parts, that is reported rather
than silently trimmed.

Token counts are approximations. They are used to decide what to include, never
to make a clinical decision, so a rough estimate is appropriate and avoids a
tokenizer dependency on the hot path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.agents.conversation_memory import ConversationMemory, MemoryScope

# Ordered most important first. Anything below the cut line is dropped when the
# budget is exhausted.
SECTION_PRIORITY: tuple[str, ...] = (
    "safety_constraints",
    "current_message",
    "canonical_state",
    "important_events",
    "rag_evidence",
    "recent_conversation",
    "rolling_summary",
    "semantic_memory",
)

# Sections that must never be dropped. If these alone exceed the budget the
# caller is told, rather than being handed a silently incomplete context.
NON_NEGOTIABLE: frozenset[str] = frozenset(
    {"safety_constraints", "current_message", "canonical_state"}
)

DEFAULT_TOKEN_BUDGET = 6000


def estimate_tokens(text: str) -> int:
    """Rough token estimate. Vietnamese averages near 3 characters per token."""
    return max(1, len(text) // 3)


@dataclass
class AssembledContext:
    """What will be sent, what was left out, and what it cost."""

    sections: dict[str, str] = field(default_factory=dict)
    included: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    estimated_tokens: int = 0
    budget: int = DEFAULT_TOKEN_BUDGET
    over_budget: bool = False
    memory_ids_used: list[str] = field(default_factory=list)

    def render(self) -> str:
        return "\n\n".join(
            f"### {name}\n{self.sections[name]}"
            for name in SECTION_PRIORITY
            if name in self.sections
        )

    def audit(self) -> dict[str, Any]:
        """Concise, structured. No chain of thought, no patient free text."""
        return {
            "sections_included": list(self.included),
            "sections_dropped": list(self.dropped),
            "estimated_tokens": self.estimated_tokens,
            "budget": self.budget,
            "over_budget": self.over_budget,
            "memory_ids": list(self.memory_ids_used),
        }


def assemble_context(
    *,
    safety_constraints: str,
    current_message: str,
    canonical_summary: str,
    memory: ConversationMemory | None = None,
    scope: MemoryScope | None = None,
    rag_evidence: str = "",
    retrieve_memory: bool = False,
    budget: int = DEFAULT_TOKEN_BUDGET,
) -> AssembledContext:
    """Build the turn context in priority order, under a token budget.

    ``retrieve_memory`` is deliberately opt-in: searching earlier conversation
    on every turn costs latency for a need that arises only when the patient
    refers back to something. The planner asks for it via RETRIEVE_MEMORY.
    """
    candidates: list[tuple[str, str]] = [
        ("safety_constraints", safety_constraints),
        ("current_message", current_message),
        ("canonical_state", canonical_summary),
    ]
    memory_ids: list[str] = []

    if memory is not None and scope is not None:
        events = memory.important_events(scope)
        if events:
            candidates.append(
                (
                    "important_events",
                    "\n".join(
                        f"- [{item.event_kind}] {item.content[:200]}" for item in events
                    ),
                )
            )
            memory_ids.extend(item.id for item in events)

    if rag_evidence:
        candidates.append(("rag_evidence", rag_evidence))

    if memory is not None and scope is not None:
        recent = memory.recent(scope)
        if recent:
            candidates.append(
                (
                    "recent_conversation",
                    "\n".join(f"- {item.source}: {item.content[:200]}" for item in recent),
                )
            )
            memory_ids.extend(item.id for item in recent)

        summary = memory.rolling_summary(scope)
        if summary is not None:
            candidates.append(("rolling_summary", summary.content))
            memory_ids.append(summary.id)

        if retrieve_memory and current_message:
            hits = memory.search(current_message, scope)
            recent_ids = {item.id for item in recent}
            older = [
                (item, score) for item, score in hits if item.id not in recent_ids
            ]
            if older:
                candidates.append(
                    (
                        "semantic_memory",
                        "\n".join(
                            f"- ({score:.2f}) {item.content[:200]}"
                            for item, score in older
                        ),
                    )
                )
                memory_ids.extend(item.id for item, _ in older)

    ordered = sorted(
        candidates, key=lambda pair: SECTION_PRIORITY.index(pair[0])
    )

    result = AssembledContext(budget=budget, memory_ids_used=memory_ids)
    running = 0
    for name, body in ordered:
        if not body:
            continue
        cost = estimate_tokens(body)
        if name in NON_NEGOTIABLE:
            result.sections[name] = body
            result.included.append(name)
            running += cost
            continue
        if running + cost > budget:
            result.dropped.append(name)
            continue
        result.sections[name] = body
        result.included.append(name)
        running += cost

    result.estimated_tokens = running
    result.over_budget = running > budget
    return result
