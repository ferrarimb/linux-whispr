"""Abstract LLM backend interface for AI text refinement."""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass
class RefinementResult:
    """Result from AI text refinement."""

    text: str
    model: str = ""
    tokens_used: int = 0


class LLMBackend(abc.ABC):
    """Abstract base class for LLM backends used in text refinement."""

    @abc.abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> RefinementResult:
        """Generate text from a system + user prompt pair.

        Args:
            system_prompt: The system/instruction prompt.
            user_prompt: The user message (raw transcription or command).

        Returns:
            RefinementResult with the generated text.
        """
        ...

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Whether this backend is currently available (model loaded, API key set, etc.)."""
        ...
