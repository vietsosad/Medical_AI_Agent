"""Public entry points for the MedTriage DeepAgent runtime."""

from src.agents.deepagent_runtime.supervisor import (
    configure_deepagent_runtime,
    get_deepagent_runtime,
    reset_deepagent_runtime,
)

__all__ = [
    "configure_deepagent_runtime",
    "get_deepagent_runtime",
    "reset_deepagent_runtime",
]
