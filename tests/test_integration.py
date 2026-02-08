"""Integration tests — verify module imports and wiring."""

from __future__ import annotations

import importlib

import pytest


class TestModuleImports:
    """Verify all modules can be imported without errors."""

    @pytest.mark.parametrize(
        "module",
        [
            "linux_whispr",
            "linux_whispr.constants",
            "linux_whispr.config",
            "linux_whispr.events",
            "linux_whispr.platform.detect",
            "linux_whispr.platform.notifications",
            "linux_whispr.platform.autostart",
            "linux_whispr.stt.base",
            "linux_whispr.stt.faster_whisper",
            "linux_whispr.stt.model_manager",
            "linux_whispr.stt.openai_api",
            "linux_whispr.stt.groq_api",
            "linux_whispr.ai.base",
            "linux_whispr.ai.refinement",
            "linux_whispr.ai.command",
            "linux_whispr.ai.openai_llm",
            "linux_whispr.ai.groq_llm",
            "linux_whispr.ai.anthropic_llm",
            "linux_whispr.ai.local_llm",
            "linux_whispr.ai.prompts.refinement",
            "linux_whispr.ai.prompts.command",
            "linux_whispr.features.dictionary",
            "linux_whispr.features.snippets",
            "linux_whispr.features.history",
            "linux_whispr.features.adaptive",
            "linux_whispr.output.clipboard",
            "linux_whispr.output.injector",
            "linux_whispr.output.xdotool",
            "linux_whispr.output.wtype",
            "linux_whispr.output.ydotool",
            "linux_whispr.input.hotkey",
            "linux_whispr.ui.overlay",
            "linux_whispr.ui.tray",
            "linux_whispr.ui.settings",
            "linux_whispr.ui.wizard",
        ],
    )
    def test_import(self, module: str) -> None:
        """Each module should import without error."""
        try:
            importlib.import_module(module)
        except OSError as e:
            if "PortAudio" in str(e):
                pytest.skip("PortAudio not available")
            raise


class TestConstants:
    def test_supported_models_list(self) -> None:
        from linux_whispr.constants import SUPPORTED_WHISPER_MODELS

        assert len(SUPPORTED_WHISPER_MODELS) >= 5
        assert "base" in SUPPORTED_WHISPER_MODELS
        assert "large-v3-turbo" in SUPPORTED_WHISPER_MODELS

    def test_xdg_paths_are_absolute(self) -> None:
        from linux_whispr.constants import CACHE_DIR, CONFIG_DIR, DATA_DIR

        assert CONFIG_DIR.is_absolute()
        assert DATA_DIR.is_absolute()
        assert CACHE_DIR.is_absolute()


class TestConfigIntegration:
    def test_default_config_round_trip(self, tmp_path: object) -> None:
        from pathlib import Path

        from linux_whispr.config import AppConfig

        p = Path(str(tmp_path)) / "test.toml"
        cfg = AppConfig()
        cfg.save(p)

        loaded = AppConfig.load(p)
        assert loaded.stt.backend == cfg.stt.backend
        assert loaded.hotkey.dictation == cfg.hotkey.dictation
        assert loaded.audio.silence_duration == cfg.audio.silence_duration


class TestEventBusIntegration:
    def test_full_pipeline_event_flow(self) -> None:
        from linux_whispr.events import EventBus

        bus = EventBus()
        trace: list[str] = []

        bus.on("hotkey.dictation.start", lambda **kw: trace.append("start"))
        bus.on("stt.started", lambda **kw: trace.append("stt"))
        bus.on("stt.complete", lambda **kw: trace.append("done"))
        bus.on("inject.complete", lambda **kw: trace.append("inject"))
        bus.on("state.change", lambda **kw: trace.append(f"state:{kw.get('new_state')}"))

        # Simulate the full pipeline
        bus.emit("hotkey.dictation.start")
        bus.emit("stt.started")
        bus.emit("stt.complete", text="hello world", language="en")
        bus.emit("inject.complete", text="hello world")
        bus.emit("state.change", old_state="PROCESSING", new_state="IDLE")

        assert trace == ["start", "stt", "done", "inject", "state:IDLE"]
        bus.clear()


class TestModelManager:
    def test_list_models(self) -> None:
        from linux_whispr.stt.model_manager import ModelManager

        mm = ModelManager()
        models = mm.list_models()
        assert len(models) >= 5
        names = [m.name for m in models]
        assert "base" in names

    def test_unsupported_model_raises(self) -> None:
        from linux_whispr.stt.model_manager import ModelManager

        mm = ModelManager()
        with pytest.raises(ValueError, match="Unsupported"):
            mm.download("nonexistent-model-xyz")
