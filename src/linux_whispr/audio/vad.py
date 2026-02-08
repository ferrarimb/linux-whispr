"""Voice Activity Detection using Silero VAD (ONNX)."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from linux_whispr.constants import (
    AUDIO_SAMPLE_RATE,
    CACHE_DIR,
    VAD_MIN_SPEECH_DURATION,
    VAD_SILENCE_DURATION,
    VAD_THRESHOLD,
)

if TYPE_CHECKING:
    import onnxruntime as ort

logger = logging.getLogger(__name__)

# Silero VAD expects 16kHz audio in chunks of 512 samples (32ms)
VAD_CHUNK_SAMPLES = 512
SILERO_VAD_URL = (
    "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.onnx"
)


class SileroVAD:
    """Silero VAD wrapper using ONNX runtime.

    Processes audio chunks and tracks speech/silence state to support
    auto-stop after a configurable silence duration.
    """

    def __init__(
        self,
        threshold: float = VAD_THRESHOLD,
        silence_duration: float = VAD_SILENCE_DURATION,
        min_speech_duration: float = VAD_MIN_SPEECH_DURATION,
        sample_rate: int = AUDIO_SAMPLE_RATE,
    ) -> None:
        self._threshold = threshold
        self._silence_duration = silence_duration
        self._min_speech_duration = min_speech_duration
        self._sample_rate = sample_rate

        self._session: ort.InferenceSession | None = None
        self._state: np.ndarray = np.zeros((2, 1, 128), dtype=np.float32)
        self._use_state_input: bool = True  # True = new format ('state'), False = old ('h', 'c')

        # State tracking
        self._speech_detected = False
        self._speech_start_time: float | None = None
        self._last_speech_time: float = 0.0

    @property
    def model_path(self) -> Path:
        """Path to the cached Silero VAD ONNX model."""
        return CACHE_DIR / "silero_vad.onnx"

    def load(self) -> None:
        """Load the Silero VAD ONNX model."""
        import onnxruntime as ort

        model_path = self.model_path
        if not model_path.exists():
            self._download_model()

        self._session = ort.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"],
        )

        # Detect model input format (v5 uses 'state', v4 uses 'h'/'c')
        input_names = [inp.name for inp in self._session.get_inputs()]
        self._use_state_input = "state" in input_names
        if not self._use_state_input:
            logger.info("Silero VAD using legacy format (h/c inputs)")

        self.reset()
        logger.info("Silero VAD loaded from %s", model_path)

    def _download_model(self) -> None:
        """Download the Silero VAD ONNX model."""
        import urllib.request

        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Downloading Silero VAD model to %s", self.model_path)
        urllib.request.urlretrieve(SILERO_VAD_URL, self.model_path)
        logger.info("Silero VAD model downloaded")

    def reset(self) -> None:
        """Reset internal state for a new recording session."""
        if self._use_state_input:
            self._state = np.zeros((2, 1, 128), dtype=np.float32)
        else:
            # Legacy format: separate h and c LSTM tensors
            self._h = np.zeros((2, 1, 64), dtype=np.float32)
            self._c = np.zeros((2, 1, 64), dtype=np.float32)
        self._speech_detected = False
        self._speech_start_time = None
        self._last_speech_time = 0.0

    def process_chunk(self, audio_int16: np.ndarray) -> float:
        """Process an audio chunk and return the speech probability.

        Args:
            audio_int16: Audio samples as int16 numpy array.

        Returns:
            Speech probability (0.0 to 1.0).
        """
        if self._session is None:
            raise RuntimeError("VAD model not loaded. Call load() first.")

        # Convert int16 to float32 normalized to [-1, 1]
        audio_float = audio_int16.astype(np.float32) / 32768.0

        # Silero VAD expects exactly 512 samples at 16kHz
        # Process in 512-sample chunks, return probability of last chunk
        prob = 0.0
        for start in range(0, len(audio_float), VAD_CHUNK_SAMPLES):
            chunk = audio_float[start : start + VAD_CHUNK_SAMPLES]
            if len(chunk) < VAD_CHUNK_SAMPLES:
                # Pad with zeros if needed
                chunk = np.pad(chunk, (0, VAD_CHUNK_SAMPLES - len(chunk)))

            chunk = chunk.reshape(1, -1)
            sr = np.array([self._sample_rate], dtype=np.int64)

            if self._use_state_input:
                ort_inputs = {
                    "input": chunk,
                    "state": self._state,
                    "sr": sr,
                }
                ort_outputs = self._session.run(None, ort_inputs)
                prob = float(ort_outputs[0].item())
                self._state = ort_outputs[1]
            else:
                ort_inputs = {
                    "input": chunk,
                    "h": self._h,
                    "c": self._c,
                    "sr": sr,
                }
                ort_outputs = self._session.run(None, ort_inputs)
                prob = float(ort_outputs[0].item())
                self._h = ort_outputs[1]
                self._c = ort_outputs[2]

        return prob

    def is_speech(self, audio_int16: np.ndarray) -> bool:
        """Process audio and return whether speech is detected above threshold."""
        prob = self.process_chunk(audio_int16)
        now = time.monotonic()

        if prob >= self._threshold:
            if not self._speech_detected:
                self._speech_detected = True
                self._speech_start_time = now
            self._last_speech_time = now
            return True

        return False

    def should_stop(self) -> bool:
        """Check if recording should auto-stop due to silence after speech.

        Returns True if:
        1. Speech was detected at some point
        2. Sufficient speech duration was recorded
        3. Silence has lasted longer than the configured duration
        """
        if not self._speech_detected:
            return False

        if self._speech_start_time is None:
            return False

        now = time.monotonic()
        speech_duration = self._last_speech_time - self._speech_start_time
        silence_duration = now - self._last_speech_time

        if speech_duration < self._min_speech_duration:
            return False

        return silence_duration >= self._silence_duration

    @property
    def speech_detected(self) -> bool:
        """Whether any speech has been detected in this session."""
        return self._speech_detected
