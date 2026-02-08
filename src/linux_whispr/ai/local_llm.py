"""Local LLM backend via llama-cpp-python for AI text refinement."""

from __future__ import annotations

import logging
from pathlib import Path

from linux_whispr.ai.base import LLMBackend, RefinementResult

logger = logging.getLogger(__name__)


class LocalLLMBackend(LLMBackend):
    """LLM backend using llama-cpp-python for local inference.

    Supports GGUF models like Qwen2.5-3B, Phi-3-mini, Gemma-2-2B.
    """

    def __init__(
        self,
        model_path: str | Path,
        n_ctx: int = 2048,
        n_gpu_layers: int = -1,
    ) -> None:
        self._model_path = Path(model_path)
        self._n_ctx = n_ctx
        self._n_gpu_layers = n_gpu_layers
        self._llm: object | None = None

    def load(self) -> None:
        """Load the GGUF model."""
        from llama_cpp import Llama

        logger.info("Loading local LLM from %s", self._model_path)
        self._llm = Llama(
            model_path=str(self._model_path),
            n_ctx=self._n_ctx,
            n_gpu_layers=self._n_gpu_layers,
            verbose=False,
        )
        logger.info("Local LLM loaded")

    def generate(self, system_prompt: str, user_prompt: str) -> RefinementResult:
        if self._llm is None:
            self.load()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = self._llm.create_chat_completion(  # type: ignore[union-attr]
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
        )

        text = response["choices"][0]["message"]["content"] or ""
        tokens = response.get("usage", {}).get("total_tokens", 0)

        return RefinementResult(
            text=text,
            model=str(self._model_path.name),
            tokens_used=tokens,
        )

    def is_available(self) -> bool:
        return self._model_path.exists()

    def unload(self) -> None:
        """Unload the model and free memory."""
        self._llm = None
        logger.info("Local LLM unloaded")
