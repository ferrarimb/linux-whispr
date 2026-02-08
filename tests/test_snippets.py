"""Tests for snippet engine."""

from __future__ import annotations

from pathlib import Path

from linux_whispr.features.snippets import SnippetEngine


class TestSnippetEngine:
    def test_expand_trigger(self, tmp_path: Path) -> None:
        engine = SnippetEngine(tmp_path / "snippets.toml")
        engine.add("my email", "joao@example.com")

        result = engine.expand("Please send it to my email thanks")
        assert result == "Please send it to joao@example.com thanks"

    def test_expand_case_insensitive(self, tmp_path: Path) -> None:
        engine = SnippetEngine(tmp_path / "snippets.toml")
        engine.add("My Email", "joao@example.com")

        result = engine.expand("send to my email")
        assert "joao@example.com" in result

    def test_no_match(self, tmp_path: Path) -> None:
        engine = SnippetEngine(tmp_path / "snippets.toml")
        engine.add("my email", "joao@example.com")

        result = engine.expand("no triggers here")
        assert result == "no triggers here"

    def test_save_and_load(self, tmp_path: Path) -> None:
        path = tmp_path / "snippets.toml"
        engine = SnippetEngine(path)
        engine.add("trigger", "expansion")

        engine2 = SnippetEngine(path)
        engine2.load()
        assert len(engine2.snippets) == 1
        assert engine2.snippets[0].trigger == "trigger"

    def test_remove(self, tmp_path: Path) -> None:
        engine = SnippetEngine(tmp_path / "snippets.toml")
        engine.add("trigger", "expansion")
        assert engine.remove("trigger")
        assert len(engine.snippets) == 0
