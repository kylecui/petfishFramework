"""Word sorting tool — deterministic alphabetical sort for BBH word_sorting task."""
from __future__ import annotations

from dataclasses import dataclass, field

from petfishframework.core.contracts import RiskLevel
from petfishframework.core.types import ToolResult

from .base import BaseTool


def _sort_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "words": {
                "type": "string",
                "description": "Words to sort alphabetically, separated by spaces.",
            }
        },
        "required": ["words"],
    }


@dataclass
class WordSorter(BaseTool):
    """Sort words alphabetically — deterministic tool for a task LLMs struggle with."""

    name: str = "word_sorter"
    description: str = "Sort a list of words alphabetically. Pass the words as a space-separated string."
    input_schema: dict = field(default_factory=_sort_schema)
    risk_level: RiskLevel = RiskLevel.LOW
    capabilities: tuple[str, ...] = ()

    def execute(self, args: dict) -> ToolResult:
        words_str = args.get("words", "")
        words = words_str.strip().split()
        if not words:
            return ToolResult(error="No words provided")
        sorted_words = sorted(words, key=str.lower)
        return ToolResult(value=" ".join(sorted_words))
