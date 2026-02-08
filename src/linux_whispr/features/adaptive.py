"""Adaptive Dictionary Learning — monitors clipboard for user corrections after injection."""

from __future__ import annotations

import difflib
import logging
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from linux_whispr.events import EventBus
    from linux_whispr.features.dictionary import Dictionary
    from linux_whispr.output.clipboard import Clipboard

logger = logging.getLogger(__name__)


class AdaptiveLearner:
    """Watches for user corrections after text injection to learn vocabulary.

    After text is injected, polls the clipboard for a configurable window.
    If the user copies text that differs from what was injected, compares
    the two to find word-level corrections and records them.
    """

    def __init__(
        self,
        event_bus: EventBus,
        dictionary: Dictionary,
        clipboard: Clipboard,
        watch_window: float = 15.0,
        poll_interval: float = 2.0,
    ) -> None:
        self._event_bus = event_bus
        self._dictionary = dictionary
        self._clipboard = clipboard
        self._watch_window = watch_window
        self._poll_interval = poll_interval
        self._enabled = True
        self._watching = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    def start_watching(self, injected_text: str) -> None:
        """Start monitoring the clipboard for corrections to the injected text."""
        if not self._enabled or not injected_text.strip():
            return

        if self._watching:
            logger.debug("Already watching, skipping")
            return

        thread = threading.Thread(
            target=self._watch_loop,
            args=(injected_text,),
            daemon=True,
            name="adaptive-learner",
        )
        thread.start()

    def _watch_loop(self, injected_text: str) -> None:
        """Poll clipboard for changes and detect corrections."""
        self._watching = True
        start_time = time.monotonic()

        logger.debug(
            "Adaptive learning: watching for corrections (%.0fs window)", self._watch_window
        )

        # Snapshot the clipboard right after injection as baseline
        # (should contain the injected text, or whatever was there before)
        baseline = self._clipboard.read() or ""

        try:
            while (time.monotonic() - start_time) < self._watch_window:
                time.sleep(self._poll_interval)

                clipboard_text = self._clipboard.read()
                if clipboard_text is None:
                    continue

                # Skip if clipboard hasn't changed from baseline
                if clipboard_text == baseline:
                    continue

                # Skip if clipboard is the same as what we injected
                if clipboard_text == injected_text:
                    continue

                if not clipboard_text.strip():
                    continue

                # Only consider it a correction if the new clipboard text
                # is sufficiently similar to the injected text (> 30%).
                # This filters out unrelated clipboard activity.
                similarity = difflib.SequenceMatcher(
                    None, injected_text.lower(), clipboard_text.lower()
                ).ratio()

                if similarity < 0.3:
                    logger.debug(
                        "Adaptive learning: clipboard change ignored (similarity=%.2f)",
                        similarity,
                    )
                    continue

                corrections = self._find_corrections(injected_text, clipboard_text)
                if corrections:
                    self._record_corrections(corrections)
                    break  # Found corrections, stop watching

                # Update baseline so we don't re-process the same change
                baseline = clipboard_text
        finally:
            self._watching = False

    def _find_corrections(
        self, original: str, corrected: str
    ) -> list[tuple[str, str]]:
        """Find word-level differences between original and corrected text.

        Returns a list of (original_word, corrected_word) tuples.
        """
        corrections: list[tuple[str, str]] = []

        orig_words = original.split()
        corr_words = corrected.split()

        # Use SequenceMatcher to align words
        matcher = difflib.SequenceMatcher(None, orig_words, corr_words)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "replace":
                # Words were replaced — these are corrections
                orig_chunk = " ".join(orig_words[i1:i2])
                corr_chunk = " ".join(corr_words[j1:j2])
                if orig_chunk.lower() != corr_chunk.lower() or orig_chunk != corr_chunk:
                    corrections.append((orig_chunk, corr_chunk))
                    logger.info(
                        "Correction detected: '%s' → '%s'", orig_chunk, corr_chunk
                    )

        return corrections

    def _record_corrections(self, corrections: list[tuple[str, str]]) -> None:
        """Record detected corrections in the dictionary."""
        for heard, corrected in corrections:
            self._dictionary.add_correction(heard, corrected)
            logger.info("Learned correction: '%s' → '%s'", heard, corrected)

        self._event_bus.emit(
            "adaptive.corrections_learned",
            count=len(corrections),
            corrections=corrections,
        )
