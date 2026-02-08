"""Shared test fixtures."""

from __future__ import annotations

import io
import wave
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from linux_whispr.config import AppConfig
from linux_whispr.events import EventBus


@pytest.fixture
def event_bus() -> EventBus:
    """Fresh event bus for each test."""
    bus = EventBus()
    yield bus
    bus.clear()


@pytest.fixture
def config() -> AppConfig:
    """Default config for testing."""
    return AppConfig()


@pytest.fixture
def tmp_config(tmp_path: Path) -> AppConfig:
    """Config that uses tmp_path for file storage."""
    cfg = AppConfig()
    return cfg


def make_wav_bytes(duration: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate silent WAV audio bytes for testing."""
    num_samples = int(duration * sample_rate)
    audio = np.zeros(num_samples, dtype=np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())

    return buf.getvalue()


def make_speech_wav_bytes(duration: float = 1.0, sample_rate: int = 16000) -> bytes:
    """Generate WAV audio bytes with a simple sine wave (simulates speech)."""
    num_samples = int(duration * sample_rate)
    t = np.linspace(0, duration, num_samples, dtype=np.float32)
    # Mix of frequencies to simulate speech-like audio
    audio = (
        0.3 * np.sin(2 * np.pi * 200 * t)
        + 0.2 * np.sin(2 * np.pi * 500 * t)
        + 0.1 * np.sin(2 * np.pi * 1000 * t)
    )
    audio_int16 = (audio * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())

    return buf.getvalue()
