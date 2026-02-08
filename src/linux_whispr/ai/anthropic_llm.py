"""Anthropic Claude backend for AI text refinement."""

from __future__ import annotations

import logging

from linux_whispr.ai.base import LLMBackend, RefinementResult

logger = logging.getLogger(__name__)


class AnthropicLLMBackend(LLMBackend):
    """LLM backend using Anthropic API (Claude Haiku, etc.)."""

    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307") -> None:
        self._api_key = api_key
        self._model = model
        self._client: object | None = None

    def load(self) -> None:
        """Initialize the Anthropic client."""
        from anthropic import Anthropic

        self._client = Anthropic(api_key=self._api_key)
        logger.info("Anthropic LLM client initialized (model=%s)", self._model)

    def generate(self, system_prompt: str, user_prompt: str) -> RefinementResult:
        if self._client is None:
            self.load()

        kwargs: dict = {
            "model": self._model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self._client.messages.create(**kwargs)  # type: ignore[union-attr]

        text = ""
        for block in response.content:
            if hasattr(block, "text"):
                text += block.text

        tokens = response.usage.input_tokens + response.usage.output_tokens

        return RefinementResult(text=text, model=self._model, tokens_used=tokens)

    def is_available(self) -> bool:
        return bool(self._api_key)
