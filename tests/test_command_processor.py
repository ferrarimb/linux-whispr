"""Tests for Command Mode processor."""

from __future__ import annotations

from unittest.mock import MagicMock

from linux_whispr.ai.base import RefinementResult
from linux_whispr.ai.command import CommandProcessor
from linux_whispr.events import EventBus


class TestCommandProcessor:
    def test_no_backend_returns_none(self) -> None:
        bus = EventBus()
        processor = CommandProcessor(event_bus=bus, backend=None)
        result = processor.process("make this formal")
        assert result is None

    def test_process_with_selected_text(self) -> None:
        bus = EventBus()
        mock_backend = MagicMock()
        mock_backend.is_available.return_value = True
        mock_backend.generate.return_value = RefinementResult(text="Formal text here")

        mock_clipboard = MagicMock()
        mock_clipboard.read.return_value = "hey whats up"

        processor = CommandProcessor(
            event_bus=bus,
            backend=mock_backend,
            clipboard=mock_clipboard,
        )
        result = processor.process("make this more formal")

        assert result == "Formal text here"
        mock_backend.generate.assert_called_once()
        # Verify the selected text was included
        call_args = mock_backend.generate.call_args
        assert "hey whats up" in call_args[1]["user_prompt"] or "hey whats up" in call_args[0][1]

    def test_process_without_clipboard(self) -> None:
        bus = EventBus()
        mock_backend = MagicMock()
        mock_backend.is_available.return_value = True
        mock_backend.generate.return_value = RefinementResult(text="Generated email")

        processor = CommandProcessor(
            event_bus=bus,
            backend=mock_backend,
            clipboard=None,
        )
        result = processor.process("write a thank you email")

        assert result == "Generated email"

    def test_backend_failure_returns_none(self) -> None:
        bus = EventBus()
        mock_backend = MagicMock()
        mock_backend.is_available.return_value = True
        mock_backend.generate.side_effect = RuntimeError("API error")

        processor = CommandProcessor(event_bus=bus, backend=mock_backend)
        result = processor.process("do something")
        assert result is None
