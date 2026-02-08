"""Tests for AI refinement pipeline and prompt templates."""

from __future__ import annotations

from unittest.mock import MagicMock

from linux_whispr.ai.base import RefinementResult
from linux_whispr.ai.prompts.command import build_command_prompt
from linux_whispr.ai.prompts.refinement import (
    build_refinement_prompt,
    detect_context,
)
from linux_whispr.ai.refinement import RefinementPipeline
from linux_whispr.events import EventBus


class TestContextDetection:
    def test_gmail_is_email(self) -> None:
        assert detect_context("Gmail - Inbox") == "email"

    def test_vscode_is_code(self) -> None:
        assert detect_context("app.py - Visual Studio Code") == "code"

    def test_slack_is_chat(self) -> None:
        assert detect_context("Slack | general") == "chat"

    def test_discord_is_chat(self) -> None:
        assert detect_context("Discord") == "chat"

    def test_unknown_is_general(self) -> None:
        assert detect_context("Some Random App") == "general"

    def test_none_is_general(self) -> None:
        assert detect_context(None) == "general"

    def test_thunderbird_is_email(self) -> None:
        assert detect_context("Thunderbird Mail") == "email"

    def test_neovim_is_code(self) -> None:
        assert detect_context("nvim - neovim") == "code"

    def test_telegram_is_chat(self) -> None:
        assert detect_context("Telegram Desktop") == "chat"


class TestBuildRefinementPrompt:
    def test_general_prompt_contains_raw_text(self) -> None:
        prompt = build_refinement_prompt("hello world")
        assert "hello world" in prompt

    def test_email_prompt_for_gmail(self) -> None:
        prompt = build_refinement_prompt("hello", app_name="Gmail - Inbox")
        assert "email" in prompt.lower()

    def test_dictionary_context_included(self) -> None:
        prompt = build_refinement_prompt(
            "hello",
            dictionary_context="SQLAlchemy (not sequel alchemy)",
        )
        assert "SQLAlchemy" in prompt

    def test_code_prompt_for_vscode(self) -> None:
        prompt = build_refinement_prompt("add comment", app_name="VS Code")
        assert "code" in prompt.lower()


class TestBuildCommandPrompt:
    def test_with_selected_text(self) -> None:
        sys_prompt, user_prompt = build_command_prompt(
            "make this formal", "hey whats up"
        )
        assert "command" in sys_prompt.lower()
        assert "make this formal" in user_prompt
        assert "hey whats up" in user_prompt

    def test_without_selected_text(self) -> None:
        sys_prompt, user_prompt = build_command_prompt("write a thank you email")
        assert "generate" in sys_prompt.lower()
        assert "write a thank you email" in user_prompt


class TestRefinementPipeline:
    def test_disabled_returns_raw_text(self) -> None:
        bus = EventBus()
        pipeline = RefinementPipeline(event_bus=bus, backend=None, enabled=False)
        result = pipeline.refine("um hello world")
        assert result == "um hello world"

    def test_enabled_no_backend_returns_raw_text(self) -> None:
        bus = EventBus()
        pipeline = RefinementPipeline(event_bus=bus, backend=None, enabled=True)
        assert not pipeline.enabled  # enabled requires backend
        result = pipeline.refine("um hello world")
        assert result == "um hello world"

    def test_enabled_with_backend_calls_generate(self) -> None:
        bus = EventBus()
        mock_backend = MagicMock()
        mock_backend.is_available.return_value = True
        mock_backend.generate.return_value = RefinementResult(
            text="Hello world", model="test", tokens_used=10
        )

        pipeline = RefinementPipeline(event_bus=bus, backend=mock_backend, enabled=True)
        result = pipeline.refine("um hello world")

        assert result == "Hello world"
        mock_backend.generate.assert_called_once()

    def test_backend_failure_returns_raw_text(self) -> None:
        bus = EventBus()
        mock_backend = MagicMock()
        mock_backend.is_available.return_value = True
        mock_backend.generate.side_effect = RuntimeError("API error")

        pipeline = RefinementPipeline(event_bus=bus, backend=mock_backend, enabled=True)
        result = pipeline.refine("hello world")

        assert result == "hello world"

    def test_emits_events(self) -> None:
        bus = EventBus()
        events: list[str] = []
        bus.on("ai.started", lambda **kw: events.append("started"))
        bus.on("ai.complete", lambda **kw: events.append("complete"))

        mock_backend = MagicMock()
        mock_backend.is_available.return_value = True
        mock_backend.generate.return_value = RefinementResult(text="refined")

        pipeline = RefinementPipeline(event_bus=bus, backend=mock_backend, enabled=True)
        pipeline.refine("raw text")

        assert "started" in events
        assert "complete" in events
