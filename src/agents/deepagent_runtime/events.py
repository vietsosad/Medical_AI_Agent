"""Stable event adapter between DeepAgent tools and the existing SSE API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class RuntimeEvent:
    event: Literal["on_chain_start", "on_chain_end"]
    name: str
    data: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {"event": self.event, "name": self.name, "data": self.data}


def phase_started(name: str) -> RuntimeEvent:
    return RuntimeEvent(event="on_chain_start", name=name, data={})


def phase_completed(name: str, output: dict[str, Any]) -> RuntimeEvent:
    return RuntimeEvent(
        event="on_chain_end",
        name=name,
        data={"output": output},
    )
