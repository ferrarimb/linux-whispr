"""Audio device enumeration."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import sounddevice as sd

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AudioDevice:
    """Represents an audio input device."""

    index: int
    name: str
    channels: int
    default_samplerate: float
    is_default: bool


def list_input_devices() -> list[AudioDevice]:
    """List all available audio input devices."""
    devices: list[AudioDevice] = []
    try:
        default_device = sd.default.device[0]  # input device index
        all_devices = sd.query_devices()

        for i, dev in enumerate(all_devices):  # type: ignore[arg-type]
            if dev["max_input_channels"] > 0:  # type: ignore[index]
                devices.append(
                    AudioDevice(
                        index=i,
                        name=dev["name"],  # type: ignore[index]
                        channels=dev["max_input_channels"],  # type: ignore[index]
                        default_samplerate=dev["default_samplerate"],  # type: ignore[index]
                        is_default=(i == default_device),
                    )
                )
    except Exception:
        logger.exception("Failed to enumerate audio devices")

    return devices
