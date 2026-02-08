"""Tests for Voice Activity Detection."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import numpy as np

from linux_whispr.audio.vad import SileroVAD


class TestSileroVAD:
    def test_initial_state(self) -> None:
        vad = SileroVAD()
        assert not vad.speech_detected

    def test_reset_clears_state(self) -> None:
        vad = SileroVAD()
        vad._speech_detected = True
        vad._speech_start_time = time.monotonic()
        vad._last_speech_time = time.monotonic()

        vad.reset()

        assert not vad.speech_detected
        assert vad._speech_start_time is None
        assert vad._last_speech_time == 0.0

    def test_should_stop_false_when_no_speech(self) -> None:
        vad = SileroVAD()
        assert not vad.should_stop()

    def test_should_stop_false_when_speech_too_short(self) -> None:
        vad = SileroVAD(min_speech_duration=1.0)
        vad._speech_detected = True
        now = time.monotonic()
        vad._speech_start_time = now
        vad._last_speech_time = now + 0.1  # only 100ms of speech

        assert not vad.should_stop()

    def test_should_stop_true_after_silence(self) -> None:
        vad = SileroVAD(silence_duration=0.5, min_speech_duration=0.1)
        now = time.monotonic()
        vad._speech_detected = True
        vad._speech_start_time = now - 5.0  # speech started 5s ago
        vad._last_speech_time = now - 1.0  # last speech was 1s ago (> 0.5s silence)

        assert vad.should_stop()

    def test_model_path(self) -> None:
        vad = SileroVAD()
        assert vad.model_path.name == "silero_vad.onnx"
        assert "linux-whispr" in str(vad.model_path)
