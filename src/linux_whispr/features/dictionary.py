"""Custom dictionary manager for improved Whisper recognition."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from linux_whispr.constants import DICTIONARY_FILE

logger = logging.getLogger(__name__)


@dataclass
class DictionaryEntry:
    """A single dictionary entry."""

    word: str
    source: str = "manual"  # "manual" | "auto-learned"
    frequency: int = 0
    added_at: str = field(default_factory=lambda: datetime.now().isoformat())
    category: str = "general"  # "personal_names" | "technical" | "brand" | "general"


@dataclass
class CorrectionPair:
    """A learned correction pair from adaptive dictionary."""

    heard: str
    corrected: str
    count: int = 1
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())


class Dictionary:
    """Manages the custom dictionary for Whisper initial_prompt context."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or DICTIONARY_FILE
        self._entries: list[DictionaryEntry] = []
        self._corrections: list[CorrectionPair] = []

    def load(self) -> None:
        """Load dictionary from JSON file."""
        if not self._path.exists():
            logger.info("No dictionary file found at %s", self._path)
            return

        try:
            with open(self._path) as f:
                data = json.load(f)

            self._entries = [DictionaryEntry(**e) for e in data.get("entries", [])]
            self._corrections = [CorrectionPair(**c) for c in data.get("corrections", [])]
            logger.info(
                "Loaded dictionary: %d entries, %d corrections",
                len(self._entries),
                len(self._corrections),
            )
        except Exception:
            logger.exception("Failed to load dictionary from %s", self._path)

    def save(self) -> None:
        """Save dictionary to JSON file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "entries": [asdict(e) for e in self._entries],
            "corrections": [asdict(c) for c in self._corrections],
        }
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug("Saved dictionary to %s", self._path)

    def add_word(
        self, word: str, source: str = "manual", category: str = "general"
    ) -> None:
        """Add a word to the dictionary."""
        # Check for duplicates
        for entry in self._entries:
            if entry.word.lower() == word.lower():
                entry.frequency += 1
                return

        self._entries.append(DictionaryEntry(word=word, source=source, category=category))
        self.save()

    def remove_word(self, word: str) -> bool:
        """Remove a word from the dictionary. Returns True if found."""
        for i, entry in enumerate(self._entries):
            if entry.word.lower() == word.lower():
                self._entries.pop(i)
                self.save()
                return True
        return False

    def add_correction(self, heard: str, corrected: str) -> None:
        """Record a correction pair for adaptive learning."""
        for pair in self._corrections:
            if pair.heard.lower() == heard.lower() and pair.corrected == corrected:
                pair.count += 1
                pair.last_seen = datetime.now().isoformat()
                self.save()
                return

        self._corrections.append(CorrectionPair(heard=heard, corrected=corrected))
        self.save()

    def build_initial_prompt(self, promotion_threshold: int = 2) -> str | None:
        """Build the Whisper initial_prompt from dictionary words.

        Includes manual entries and auto-learned words that have been
        confirmed enough times (count >= promotion_threshold).
        """
        words: list[str] = []

        for entry in self._entries:
            if entry.source == "manual" or entry.frequency >= promotion_threshold:
                words.append(entry.word)

        for pair in self._corrections:
            if pair.count >= promotion_threshold:
                words.append(pair.corrected)

        if not words:
            return None

        # Whisper uses the initial_prompt as context, so we format as a natural sentence
        unique_words = list(dict.fromkeys(words))  # preserve order, dedupe
        return "Context words: " + ", ".join(unique_words) + "."

    @property
    def entries(self) -> list[DictionaryEntry]:
        return self._entries

    @property
    def corrections(self) -> list[CorrectionPair]:
        return self._corrections
