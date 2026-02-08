"""Groq LLM backend for AI text refinement (ultra-fast inference)."""

from __future__ import annotations

import logging

from linux_whispr.ai.base import LLMBackend, RefinementResult

logger = logging.getLogger(__name__)


class GroqLLMBackend(LLMBackend):
    """LLM backend using Groq API (Llama, Mixtral, etc.)."""

    def __init__(self, api_key: str, model: str = "llama-3.1-8b-instant") -> None:
        self._api_key = api_key
        self._model = model
        self._client: object | None = None

    def load(self) -> None:
        """Initialize the Groq client."""
        from groq import Groq

        self._client = Groq(api_key=self._api_key)
        logger.info("Groq LLM client initialized (model=%s)", self._model)

    def generate(self, system_prompt: str, user_prompt: str) -> RefinementResult:
        if self._client is None:
            self.load()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = self._client.chat.completions.create(  # type: ignore[union-attr]
            model=self._model,
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
        )

        text = response.choices[0].message.content or ""
        tokens = response.usage.total_tokens if response.usage else 0

        return RefinementResult(text=text, model=self._model, tokens_used=tokens)

    def is_available(self) -> bool:
        return bool(self._api_key)
