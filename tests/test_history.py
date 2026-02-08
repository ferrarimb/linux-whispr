"""Tests for transcription history."""

from __future__ import annotations

from pathlib import Path

from linux_whispr.features.history import HistoryManager


class TestHistoryManager:
    def test_add_and_search(self, tmp_path: Path) -> None:
        hm = HistoryManager(tmp_path / "history.db")
        hm.open()

        hm.add("hello world", app_context="Firefox", language="en")
        hm.add("goodbye world", app_context="VS Code")

        results = hm.search("hello")
        assert len(results) == 1
        assert results[0].raw_text == "hello world"

        hm.close()

    def test_get_recent(self, tmp_path: Path) -> None:
        hm = HistoryManager(tmp_path / "history.db")
        hm.open()

        for i in range(5):
            hm.add(f"entry {i}")

        recent = hm.get_recent(limit=3)
        assert len(recent) == 3

        hm.close()

    def test_delete(self, tmp_path: Path) -> None:
        hm = HistoryManager(tmp_path / "history.db")
        hm.open()

        entry_id = hm.add("to delete")
        assert hm.delete(entry_id)

        results = hm.search("to delete")
        assert len(results) == 0

        hm.close()

    def test_clear(self, tmp_path: Path) -> None:
        hm = HistoryManager(tmp_path / "history.db")
        hm.open()

        hm.add("one")
        hm.add("two")
        deleted = hm.clear()
        assert deleted == 2

        assert len(hm.get_recent()) == 0

        hm.close()

    def test_word_count(self, tmp_path: Path) -> None:
        hm = HistoryManager(tmp_path / "history.db")
        hm.open()

        hm.add("one two three four five")
        recent = hm.get_recent(limit=1)
        assert recent[0].word_count == 5

        hm.close()
