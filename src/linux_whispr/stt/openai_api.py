"""OpenAI Whisper API STT backend."""

from __future__ import annotations

import io
import logging
import wave

from linux_whispr.stt.base import STTBackend, TranscriptionResult

logger = logging.getLogger(__name__)


class OpenAIWhisperBackend(STTBackend):
    """STT backend using the OpenAI Whisper API."""

    def __init__(self, api_key: str, model: str = "whisper-1") -> None:
        self._api_key = api_key
        self._model = model
        self._client: object | None = None

    def load(self) -> None:
        """Initialize the OpenAI client."""
        from openai import OpenAI

        self._client = OpenAI(api_key=self._api_key)
        logger.info("OpenAI Whisper API client initialized")

    def transcribe(
        self,
        audio_bytes: bytes,
        language: str | None = None,
        initial_prompt: str | None = None,
    ) -> TranscriptionResult:
        if self._client is None:
            raise RuntimeError("Client not initialized. Call load() first.")

        # Get audio duration
        audio_file = io.BytesIO(audio_bytes)
        with wave.open(audio_file, "rb") as wf:
            duration = wf.getnframes() / wf.getframerate()
        audio_file.seek(0)

        # OpenAI API expects a file-like object with a name
        audio_file.name = "audio.wav"

        kwargs: dict = {
            "model": self._model,
            "file": audio_file,
            "response_format": "verbose_json",
        }
        if language:
            kwargs["language"] = language
        if initial_prompt:
            kwargs["prompt"] = initial_prompt

        logger.info("Transcribing %.1fs via OpenAI Whisper API", duration)
        result = self._client.audio.transcriptions.create(**kwargs)  # type: ignore[union-attr]

        return TranscriptionResult(
            text=result.text,
            language=getattr(result, "language", language),
            confidence=0.0,
            duration=duration,
        )

    def unload(self) -> None:
        self._client = None

    @property
    def is_loaded(self) -> bool:
        return self._client is not None
