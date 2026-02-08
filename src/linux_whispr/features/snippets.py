"""Snippet trigger/expansion engine."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import tomli_w

from linux_whispr.constants import SNIPPETS_FILE

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

logger = logging.getLogger(__name__)


@dataclass
class Snippet:
    """A voice snippet: trigger phrase → expanded text."""

    trigger: str
    expansion: str


class SnippetEngine:
    """Matches transcribed text against user-defined trigger phrases and expands them."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or SNIPPETS_FILE
        self._snippets: list[Snippet] = []

    def load(self) -> None:
        """Load snippets from TOML file."""
        if not self._path.exists():
            logger.info("No snippets file found at %s", self._path)
            return

        try:
            with open(self._path, "rb") as f:
                data = tomllib.load(f)

            self._snippets = [
                Snippet(trigger=s["trigger"], expansion=s["expansion"])
                for s in data.get("snippets", [])
            ]
            logger.info("Loaded %d snippet(s)", len(self._snippets))
        except Exception:
            logger.exception("Failed to load snippets from %s", self._path)

    def save(self) -> None:
        """Save snippets to TOML file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "snippets": [
                {"trigger": s.trigger, "expansion": s.expansion} for s in self._snippets
            ]
        }
        with open(self._path, "wb") as f:
            tomli_w.dump(data, f)

    def expand(self, text: str) -> str:
        """Expand any trigger phrases found in the text.

        Case-insensitive matching. Replaces the trigger phrase with its expansion.
        """
        result = text
        for snippet in self._snippets:
            # Case-insensitive replacement
            lower_result = result.lower()
            lower_trigger = snippet.trigger.lower()
            idx = lower_result.find(lower_trigger)
            while idx != -1:
                result = result[:idx] + snippet.expansion + result[idx + len(snippet.trigger) :]
                lower_result = result.lower()
                idx = lower_result.find(lower_trigger, idx + len(snippet.expansion))

        return result

    def add(self, trigger: str, expansion: str) -> None:
        """Add a new snippet."""
        self._snippets.append(Snippet(trigger=trigger, expansion=expansion))
        self.save()

    def remove(self, trigger: str) -> bool:
        """Remove a snippet by trigger. Returns True if found."""
        for i, s in enumerate(self._snippets):
            if s.trigger.lower() == trigger.lower():
                self._snippets.pop(i)
                self.save()
                return True
        return False

    @property
    def snippets(self) -> list[Snippet]:
        return self._snippets
