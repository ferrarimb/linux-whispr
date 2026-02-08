"""Microphone recording via sounddevice."""

from __future__ import annotations

import io
import logging
import threading
import time
import wave
from typing import TYPE_CHECKING

import numpy as np
import sounddevice as sd

from linux_whispr.constants import (
    AUDIO_BLOCKSIZE,
    AUDIO_CHANNELS,
    AUDIO_DTYPE,
    AUDIO_SAMPLE_RATE,
    MAX_RECORDING_DURATION,
)

if TYPE_CHECKING:
    from linux_whispr.events import EventBus

logger = logging.getLogger(__name__)


class AudioCapture:
    """Records audio from the microphone and emits events via the event bus."""

    def __init__(
        self,
        event_bus: EventBus,
        sample_rate: int = AUDIO_SAMPLE_RATE,
        device: int | str | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._sample_rate = sample_rate
        self._device = device
        self._recording = False
        self._frames: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self._start_time: float = 0.0

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def duration(self) -> float:
        """Current recording duration in seconds."""
        if not self._recording:
            return 0.0
        return time.monotonic() - self._start_time

    def start(self) -> None:
        """Start recording audio from the microphone."""
        with self._lock:
            if self._recording:
                logger.warning("Already recording")
                return

            self._frames = []
            self._recording = True
            self._start_time = time.monotonic()

            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=AUDIO_CHANNELS,
                dtype=AUDIO_DTYPE,
                blocksize=AUDIO_BLOCKSIZE,
                device=self._device,
                callback=self._audio_callback,
            )
            self._stream.start()
            logger.info("Recording started (device=%s, rate=%d)", self._device, self._sample_rate)

    def stop(self) -> bytes | None:
        """Stop recording and return WAV bytes, or None if no audio captured."""
        with self._lock:
            if not self._recording:
                logger.warning("Not recording")
                return None

            self._recording = False
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            duration = time.monotonic() - self._start_time
            logger.info("Recording stopped (duration=%.1fs, frames=%d)", duration, len(self._frames))

            if not self._frames:
                logger.warning("No audio frames captured")
                return None

            audio_data = np.concatenate(self._frames, axis=0)
            wav_bytes = self._to_wav(audio_data)

            self._event_bus.emit("audio.ready", wav_bytes=wav_bytes, duration=duration)
            return wav_bytes

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        """Called by sounddevice for each audio block."""
        if status:
            logger.warning("Audio callback status: %s", status)

        if not self._recording:
            return

        # Check max duration
        if self.duration >= MAX_RECORDING_DURATION:
            logger.warning("Max recording duration reached, auto-stopping")
            # Schedule stop on a separate thread to avoid deadlock
            threading.Thread(target=self.stop, daemon=True).start()
            return

        self._frames.append(indata.copy())

        # Emit audio level for UI (RMS of the block)
        rms = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
        # Normalize int16 RMS to 0.0-1.0 range
        level = min(1.0, rms / 32768.0 * 10.0)
        self._event_bus.emit("audio.level", level=level)

    def _to_wav(self, audio_data: np.ndarray) -> bytes:
        """Convert numpy audio array to WAV bytes."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(AUDIO_CHANNELS)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(self._sample_rate)
            wf.writeframes(audio_data.tobytes())
        return buf.getvalue()
