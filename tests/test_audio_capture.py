"""Tests for audio capture service."""

from __future__ import annotations

import io
import wave
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

try:
    from linux_whispr.audio.capture import AudioCapture

    _HAS_PORTAUDIO = True
except OSError:
    _HAS_PORTAUDIO = False

from linux_whispr.events import EventBus

pytestmark = pytest.mark.skipif(not _HAS_PORTAUDIO, reason="PortAudio library not found")


class TestAudioCapture:
    def test_initial_state(self) -> None:
        bus = EventBus()
        capture = AudioCapture(event_bus=bus)
        assert not capture.is_recording
        assert capture.duration == 0.0

    def test_stop_without_start_returns_none(self) -> None:
        bus = EventBus()
        capture = AudioCapture(event_bus=bus)
        result = capture.stop()
        assert result is None

    def test_to_wav_produces_valid_wav(self) -> None:
        bus = EventBus()
        capture = AudioCapture(event_bus=bus, sample_rate=16000)
        audio = np.zeros(16000, dtype=np.int16)  # 1 second of silence
        wav_bytes = capture._to_wav(audio)

        assert wav_bytes is not None
        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            assert wf.getnchannels() == 1
            assert wf.getsampwidth() == 2
            assert wf.getframerate() == 16000
            assert wf.getnframes() == 16000

    def test_audio_ready_event_emitted_on_stop(self) -> None:
        bus = EventBus()
        capture = AudioCapture(event_bus=bus, sample_rate=16000)
        received: list[dict] = []
        bus.on("audio.ready", lambda **kw: received.append(dict(kw)))

        # Manually set recording state and add frames
        capture._recording = True
        capture._start_time = 0.0
        capture._frames = [np.zeros((1024, 1), dtype=np.int16)]

        wav = capture.stop()
        assert wav is not None
        assert len(received) == 1
        assert "wav_bytes" in received[0]
        assert "duration" in received[0]

    def test_audio_level_event_emitted(self) -> None:
        bus = EventBus()
        capture = AudioCapture(event_bus=bus, sample_rate=16000)
        levels: list[float] = []
        bus.on("audio.level", lambda level, **kw: levels.append(level))

        capture._recording = True
        capture._start_time = 1e9  # far future so duration doesn't trigger max

        # Simulate callback with audio data
        indata = np.random.randint(-1000, 1000, size=(1024, 1), dtype=np.int16)
        import sounddevice as sd

        capture._audio_callback(indata, 1024, None, sd.CallbackFlags())

        assert len(levels) == 1
        assert 0.0 <= levels[0] <= 1.0
        assert len(capture._frames) == 1
