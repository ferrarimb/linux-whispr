"""Tests for adaptive dictionary learning."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from linux_whispr.events import EventBus
from linux_whispr.features.adaptive import AdaptiveLearner
from linux_whispr.features.dictionary import Dictionary


class TestAdaptiveLearner:
    def test_find_corrections_simple_replace(self, tmp_path: Path) -> None:
        bus = EventBus()
        dictionary = Dictionary(tmp_path / "dict.json")
        clipboard = MagicMock()

        learner = AdaptiveLearner(
            event_bus=bus,
            dictionary=dictionary,
            clipboard=clipboard,
        )

        corrections = learner._find_corrections(
            "deploy the new CRT using cube control",
            "deploy the new CRD using kubectl",
        )

        assert len(corrections) == 2
        # Should find CRT → CRD and "cube control" → "kubectl"
        originals = [c[0] for c in corrections]
        corrected = [c[1] for c in corrections]
        assert "CRT" in originals
        assert "CRD" in corrected

    def test_find_corrections_case_change(self, tmp_path: Path) -> None:
        bus = EventBus()
        dictionary = Dictionary(tmp_path / "dict.json")
        clipboard = MagicMock()

        learner = AdaptiveLearner(
            event_bus=bus,
            dictionary=dictionary,
            clipboard=clipboard,
        )

        corrections = learner._find_corrections(
            "we use kubernetes for deployment",
            "we use Kubernetes for deployment",
        )

        assert len(corrections) == 1
        assert corrections[0] == ("kubernetes", "Kubernetes")

    def test_no_corrections_when_identical(self, tmp_path: Path) -> None:
        bus = EventBus()
        dictionary = Dictionary(tmp_path / "dict.json")
        clipboard = MagicMock()

        learner = AdaptiveLearner(
            event_bus=bus,
            dictionary=dictionary,
            clipboard=clipboard,
        )

        corrections = learner._find_corrections("hello world", "hello world")
        assert len(corrections) == 0

    def test_record_corrections_updates_dictionary(self, tmp_path: Path) -> None:
        bus = EventBus()
        dictionary = Dictionary(tmp_path / "dict.json")
        clipboard = MagicMock()

        events: list[dict] = []
        bus.on("adaptive.corrections_learned", lambda **kw: events.append(dict(kw)))

        learner = AdaptiveLearner(
            event_bus=bus,
            dictionary=dictionary,
            clipboard=clipboard,
        )

        learner._record_corrections([("kubernetes", "Kubernetes")])

        assert len(dictionary.corrections) == 1
        assert dictionary.corrections[0].heard == "kubernetes"
        assert dictionary.corrections[0].corrected == "Kubernetes"
        assert len(events) == 1
        assert events[0]["count"] == 1

    def test_disabled_learner_doesnt_watch(self, tmp_path: Path) -> None:
        bus = EventBus()
        dictionary = Dictionary(tmp_path / "dict.json")
        clipboard = MagicMock()

        learner = AdaptiveLearner(
            event_bus=bus,
            dictionary=dictionary,
            clipboard=clipboard,
        )
        learner.enabled = False

        # Should not start watching
        learner.start_watching("some text")
        assert not learner._watching
