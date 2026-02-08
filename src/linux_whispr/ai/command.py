"""Command Mode processing — interprets voice commands for text transformation/generation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from linux_whispr.ai.prompts.command import build_command_prompt

if TYPE_CHECKING:
    from linux_whispr.ai.base import LLMBackend
    from linux_whispr.events import EventBus
    from linux_whispr.output.clipboard import Clipboard

logger = logging.getLogger(__name__)


class CommandProcessor:
    """Processes Command Mode voice commands.

    Reads selected text from clipboard, sends command + context to LLM,
    returns the result for injection.
    """

    def __init__(
        self,
        event_bus: EventBus,
        backend: LLMBackend | None = None,
        clipboard: "Clipboard | None" = None,
    ) -> None:
        self._event_bus = event_bus
        self._backend = backend
        self._clipboard = clipboard

    def process(self, command_text: str) -> str | None:
        """Process a voice command.

        Args:
            command_text: The transcribed command from the user.

        Returns:
            The resulting text to inject, or None on failure.
        """
        if self._backend is None or not self._backend.is_available():
            logger.error("No LLM backend available for Command Mode")
            return None

        # Read selected text from clipboard (if any)
        selected_text: str | None = None
        if self._clipboard is not None:
            selected_text = self._clipboard.read()
            if selected_text:
                logger.info("Command Mode: selected text (%d chars)", len(selected_text))

        system_prompt, user_prompt = build_command_prompt(
            command_text=command_text,
            selected_text=selected_text,
        )

        try:
            result = self._backend.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            logger.info("Command result: %d chars", len(result.text))
            return result.text.strip()
        except Exception:
            logger.exception("Command processing failed")
            return None
