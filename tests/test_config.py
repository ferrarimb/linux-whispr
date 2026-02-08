"""Tests for configuration loading and saving."""

from __future__ import annotations

from pathlib import Path

from linux_whispr.config import AppConfig


class TestAppConfig:
    def test_default_config(self) -> None:
        config = AppConfig()
        assert config.stt.backend == "faster-whisper"
        assert config.stt.model == "base"
        assert config.hotkey.dictation == "F12"
        assert config.hotkey.mode == "toggle"
        assert config.ai.enabled is False
        assert config.first_run is True

    def test_save_and_load(self, tmp_path: Path) -> None:
        config = AppConfig()
        config.stt.model = "large-v3-turbo"
        config.hotkey.dictation = "F8"
        config.first_run = False

        config_path = tmp_path / "config.toml"
        config.save(config_path)

        loaded = AppConfig.load(config_path)
        assert loaded.stt.model == "large-v3-turbo"
        assert loaded.hotkey.dictation == "F8"
        assert loaded.first_run is False

    def test_load_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        config = AppConfig.load(tmp_path / "nonexistent.toml")
        assert config.stt.backend == "faster-whisper"
        assert config.first_run is True

    def test_partial_config_preserves_defaults(self, tmp_path: Path) -> None:
        config_path = tmp_path / "partial.toml"
        config_path.write_text('[stt]\nmodel = "small"\n')

        loaded = AppConfig.load(config_path)
        assert loaded.stt.model == "small"
        assert loaded.stt.backend == "faster-whisper"  # default preserved
        assert loaded.hotkey.dictation == "F12"  # default preserved
