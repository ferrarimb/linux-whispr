"""Tests for custom dictionary."""

from __future__ import annotations

from pathlib import Path

from linux_whispr.features.dictionary import Dictionary


class TestDictionary:
    def test_add_and_build_prompt(self, tmp_path: Path) -> None:
        d = Dictionary(tmp_path / "dict.json")
        d.add_word("Kubernetes")
        d.add_word("SQLAlchemy", category="technical")

        prompt = d.build_initial_prompt()
        assert prompt is not None
        assert "Kubernetes" in prompt
        assert "SQLAlchemy" in prompt

    def test_save_and_load(self, tmp_path: Path) -> None:
        path = tmp_path / "dict.json"
        d = Dictionary(path)
        d.add_word("TestWord")
        d.save()

        d2 = Dictionary(path)
        d2.load()
        assert len(d2.entries) == 1
        assert d2.entries[0].word == "TestWord"

    def test_remove_word(self, tmp_path: Path) -> None:
        d = Dictionary(tmp_path / "dict.json")
        d.add_word("ToRemove")
        assert d.remove_word("toremove")  # case-insensitive
        assert len(d.entries) == 0

    def test_duplicate_word_increments_frequency(self, tmp_path: Path) -> None:
        d = Dictionary(tmp_path / "dict.json")
        d.add_word("Dupe")
        d.add_word("Dupe")
        assert len(d.entries) == 1
        assert d.entries[0].frequency == 1

    def test_correction_pairs(self, tmp_path: Path) -> None:
        d = Dictionary(tmp_path / "dict.json")
        d.add_correction("sequel alchemy", "SQLAlchemy")
        d.add_correction("sequel alchemy", "SQLAlchemy")

        assert len(d.corrections) == 1
        assert d.corrections[0].count == 2

        # Should appear in prompt after meeting threshold
        prompt = d.build_initial_prompt(promotion_threshold=2)
        assert prompt is not None
        assert "SQLAlchemy" in prompt
