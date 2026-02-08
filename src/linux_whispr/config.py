"""Configuration loading and saving (TOML)."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomli_w

from linux_whispr.constants import (
    AUDIO_SAMPLE_RATE,
    CLIPBOARD_RESTORE_DELAY,
    CONFIG_DIR,
    CONFIG_FILE,
    CORRECTION_PROMOTION_THRESHOLD,
    CORRECTION_WATCH_WINDOW,
    DEFAULT_COMMAND_HOTKEY,
    DEFAULT_DICTATION_HOTKEY,
    DEFAULT_WHISPER_MODEL,
    HISTORY_RETENTION_DAYS,
    VAD_SILENCE_DURATION,
    VAD_THRESHOLD,
    WEB_DEFAULT_PORT,
)

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """Audio capture configuration."""

    sample_rate: int = AUDIO_SAMPLE_RATE
    device: str | None = None  # None = default device
    silence_threshold: float = VAD_THRESHOLD
    silence_duration: float = VAD_SILENCE_DURATION
    whisper_mode: bool = False
    whisper_mode_gain: float = 3.0


@dataclass
class STTConfig:
    """Speech-to-text configuration."""

    backend: str = "faster-whisper"  # "faster-whisper" | "openai" | "groq"
    model: str = DEFAULT_WHISPER_MODEL
    language: str = "pt"  # ISO 639-1 code: "pt", "en", etc. Use "auto" for auto-detect
    device: str = "auto"  # "auto" | "cpu" | "cuda"
    compute_type: str = "auto"  # "auto" | "float16" | "int8" | "float32"


@dataclass
class AIConfig:
    """AI refinement configuration."""

    enabled: bool = False
    backend: str = "none"  # "none" | "local" | "openai" | "anthropic" | "groq" | "google"
    model: str = ""
    custom_prompt: str = ""


@dataclass
class HotkeyConfig:
    """Hotkey configuration."""

    dictation: str = DEFAULT_DICTATION_HOTKEY
    command: str = DEFAULT_COMMAND_HOTKEY
    mode: str = "toggle"  # "toggle" | "push-to-talk"


@dataclass
class InjectionConfig:
    """Text injection configuration."""

    method: str = "auto"  # "auto" | "wtype" | "xdotool" | "ydotool" | "clipboard-only"
    preserve_clipboard: bool = False
    clipboard_restore_delay: float = CLIPBOARD_RESTORE_DELAY


@dataclass
class HistoryConfig:
    """Transcription history configuration."""

    enabled: bool = True
    retention_days: int = HISTORY_RETENTION_DAYS


@dataclass
class AdaptiveConfig:
    """Adaptive dictionary learning configuration."""

    enabled: bool = True
    watch_window: int = CORRECTION_WATCH_WINDOW
    promotion_threshold: int = CORRECTION_PROMOTION_THRESHOLD


@dataclass
class WebConfig:
    """Web dashboard configuration."""

    enabled: bool = True
    port: int = WEB_DEFAULT_PORT
    auto_open: bool = True


@dataclass
class AppConfig:
    """Root application configuration."""

    audio: AudioConfig = field(default_factory=AudioConfig)
    stt: STTConfig = field(default_factory=STTConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    injection: InjectionConfig = field(default_factory=InjectionConfig)
    history: HistoryConfig = field(default_factory=HistoryConfig)
    adaptive: AdaptiveConfig = field(default_factory=AdaptiveConfig)
    web: WebConfig = field(default_factory=WebConfig)
    autostart: bool = False
    first_run: bool = True

    @classmethod
    def load(cls, path: Path | None = None) -> AppConfig:
        """Load config from TOML file, falling back to defaults."""
        config_path = path or CONFIG_FILE
        config = cls()

        if not config_path.exists():
            logger.info("No config file found at %s, using defaults", config_path)
            return config

        try:
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
            config = _merge_config(config, data)
            logger.info("Loaded config from %s", config_path)
        except Exception:
            logger.exception("Failed to load config from %s, using defaults", config_path)

        return config

    def save(self, path: Path | None = None) -> None:
        """Save config to TOML file."""
        config_path = path or CONFIG_FILE
        config_path.parent.mkdir(parents=True, exist_ok=True)

        data = _config_to_dict(self)
        with open(config_path, "wb") as f:
            tomli_w.dump(data, f)
        logger.info("Saved config to %s", config_path)


def _merge_config(config: AppConfig, data: dict[str, Any]) -> AppConfig:
    """Merge a TOML dict into an AppConfig, preserving defaults for missing keys."""
    if "audio" in data:
        for key, val in data["audio"].items():
            if hasattr(config.audio, key):
                setattr(config.audio, key, val)

    if "stt" in data:
        for key, val in data["stt"].items():
            if hasattr(config.stt, key):
                setattr(config.stt, key, val)

    if "ai" in data:
        for key, val in data["ai"].items():
            if hasattr(config.ai, key):
                setattr(config.ai, key, val)

    if "hotkey" in data:
        for key, val in data["hotkey"].items():
            if hasattr(config.hotkey, key):
                setattr(config.hotkey, key, val)

    if "injection" in data:
        for key, val in data["injection"].items():
            if hasattr(config.injection, key):
                setattr(config.injection, key, val)

    if "history" in data:
        for key, val in data["history"].items():
            if hasattr(config.history, key):
                setattr(config.history, key, val)

    if "adaptive" in data:
        for key, val in data["adaptive"].items():
            if hasattr(config.adaptive, key):
                setattr(config.adaptive, key, val)

    if "web" in data:
        for key, val in data["web"].items():
            if hasattr(config.web, key):
                setattr(config.web, key, val)

    if "autostart" in data:
        config.autostart = data["autostart"]
    if "first_run" in data:
        config.first_run = data["first_run"]

    return config


def _config_to_dict(config: AppConfig) -> dict[str, Any]:
    """Convert AppConfig to a dict suitable for TOML serialization."""
    from dataclasses import asdict

    data = asdict(config)
    # Remove None values (TOML doesn't support null)
    return _strip_none(data)


def _strip_none(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively remove None values from a dict."""
    result: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _strip_none(v)
        elif v is not None:
            result[k] = v
    return result
