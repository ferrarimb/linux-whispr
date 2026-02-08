"""Tests for STT backend interfaces."""

from __future__ import annotations

import io
import wave

import numpy as np

from linux_whispr.stt.base import STTBackend, TranscriptionResult
from linux_whispr.stt.faster_whisper import FasterWhisperBackend


class TestSTTBackendInterface:
    def test_transcription_result_defaults(self) -> None:
        result = TranscriptionResult(text="hello world")
        assert result.text == "hello world"
        assert result.language is None
        assert result.confidence == 0.0
        assert result.duration == 0.0

    def test_transcription_result_with_all_fields(self) -> None:
        result = TranscriptionResult(
            text="hello",
            language="en",
            confidence=0.95,
            duration=2.5,
        )
        assert result.language == "en"
        assert result.confidence == 0.95
        assert result.duration == 2.5


class TestFasterWhisperBackend:
    def test_initial_state(self) -> None:
        backend = FasterWhisperBackend(model_name="base")
        assert not backend.is_loaded

    def test_unload_when_not_loaded(self) -> None:
        backend = FasterWhisperBackend(model_name="base")
        backend.unload()  # Should not raise
        assert not backend.is_loaded

    def test_transcribe_without_load_raises(self) -> None:
        backend = FasterWhisperBackend(model_name="base")
        # Create minimal WAV
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(np.zeros(16000, dtype=np.int16).tobytes())

        try:
            backend.transcribe(buf.getvalue())
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "not loaded" in str(e).lower()
