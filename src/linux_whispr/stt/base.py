"""Abstract STT backend interface."""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    """Result from an STT transcription."""

    text: str
    language: str | None = None
    confidence: float = 0.0
    duration: float = 0.0  # audio duration in seconds


class STTBackend(abc.ABC):
    """Abstract base class for speech-to-text backends."""

    @abc.abstractmethod
    def load(self) -> None:
        """Load/initialize the STT model or connection."""
        ...

    @abc.abstractmethod
    def transcribe(
        self,
        audio_bytes: bytes,
        language: str | None = None,
        initial_prompt: str | None = None,
    ) -> TranscriptionResult:
        """Transcribe audio bytes to text.

        Args:
            audio_bytes: WAV audio data.
            language: Language code (e.g., "en"), or None for auto-detect.
            initial_prompt: Context hint for the model (custom dictionary words).

        Returns:
            TranscriptionResult with the transcribed text.
        """
        ...

    @abc.abstractmethod
    def unload(self) -> None:
        """Unload the model and free resources."""
        ...

    @property
    @abc.abstractmethod
    def is_loaded(self) -> bool:
        """Whether the model is currently loaded."""
        ...
