"""Shared data models for the LLM layer."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """A single tool call requested by the LLM."""

    id: str
    name: str
    arguments: dict[str, Any]  # already JSON-parsed


@dataclass
class LLMResponse:
    """Normalised response from any LLM call."""

    content: str
    model: str
    tokens_in: int
    tokens_out: int
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)
