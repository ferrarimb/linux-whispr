"""Main application orchestrator — wires all components together."""

from __future__ import annotations

import logging
import subprocess
import threading
from enum import Enum, auto
from typing import TYPE_CHECKING

from linux_whispr.audio.capture import AudioCapture
from linux_whispr.audio.vad import SileroVAD
from linux_whispr.config import AppConfig
from linux_whispr.events import EventBus, event_bus
from linux_whispr.features.adaptive import AdaptiveLearner
from linux_whispr.features.dictionary import Dictionary
from linux_whispr.features.history import HistoryManager
from linux_whispr.features.snippets import SnippetEngine
from linux_whispr.input.hotkey import create_hotkey_listener
from linux_whispr.output.clipboard import Clipboard
from linux_whispr.output.injector import TextInjector
from linux_whispr.platform.detect import PlatformInfo, detect_platform
from linux_whispr.stt.base import STTBackend
from linux_whispr.stt.faster_whisper import FasterWhisperBackend
from linux_whispr.ui.overlay import Overlay

logger = logging.getLogger(__name__)


class AppState(Enum):
    """Application states."""

    IDLE = auto()
    RECORDING = auto()
    PROCESSING = auto()
    ERROR = auto()


class LinuxWhispr:
    """Main application class that orchestrates the dictation pipeline.

    Pipeline: Hotkey → Record → VAD auto-stop → STT → Snippets → (AI refinement) → Inject → History
    """

    def __init__(self, config: AppConfig | None = None) -> None:
        self._config = config or AppConfig.load()
        self._event_bus: EventBus = event_bus
        self._state = AppState.IDLE
        self._platform: PlatformInfo | None = None

        # Core components (initialized in setup())
        self._audio: AudioCapture | None = None
        self._vad: SileroVAD | None = None
        self._stt: STTBackend | None = None
        self._injector: TextInjector | None = None
        self._clipboard: Clipboard | None = None
        self._hotkey_listener: object | None = None

        # Feature components
        self._dictionary: Dictionary | None = None
        self._snippets: SnippetEngine | None = None
        self._history: HistoryManager | None = None
        self._adaptive: AdaptiveLearner | None = None

        # UI components
        self._overlay: Overlay | None = None
        self._tray: object | None = None

        # AI refinement
        self._refinement: object | None = None

        # Web dashboard
        self._web_server: object | None = None
        self._web_thread: threading.Thread | None = None

        # VAD monitoring
        self._vad_thread: threading.Thread | None = None
        self._vad_active = False

        # Track last transcription for history
        self._last_raw_text: str = ""
        self._last_duration: float = 0.0
        self._last_language: str | None = None

    @property
    def state(self) -> AppState:
        return self._state

    def setup(self) -> None:
        """Initialize all components."""
        logger.info("Setting up LinuxWhispr...")

        # Detect platform
        self._platform = detect_platform()

        # Initialize clipboard (used by injector, adaptive learner, etc.)
        self._clipboard = Clipboard(self._platform)

        # Initialize audio capture
        self._audio = AudioCapture(
            event_bus=self._event_bus,
            sample_rate=self._config.audio.sample_rate,
            device=self._config.audio.device,
        )

        # Initialize VAD
        self._vad = SileroVAD(
            threshold=self._config.audio.silence_threshold,
            silence_duration=self._config.audio.silence_duration,
        )
        self._vad.load()

        # Initialize STT
        self._stt = self._create_stt_backend()

        # Initialize text injector
        self._injector = TextInjector(
            event_bus=self._event_bus,
            platform=self._platform,
            preserve_clipboard=self._config.injection.preserve_clipboard,
            restore_delay=self._config.injection.clipboard_restore_delay,
            method=self._config.injection.method,
        )

        # Initialize features
        self._dictionary = Dictionary()
        self._dictionary.load()

        self._snippets = SnippetEngine()
        self._snippets.load()

        self._history = HistoryManager()
        self._history.open()

        self._adaptive = AdaptiveLearner(
            event_bus=self._event_bus,
            dictionary=self._dictionary,
            clipboard=self._clipboard,
            watch_window=self._config.adaptive.watch_window,
            poll_interval=2.0,
        )
        self._adaptive.enabled = self._config.adaptive.enabled

        # Initialize AI refinement (if configured)
        self._setup_ai_refinement()

        # Initialize overlay
        self._overlay = Overlay(self._event_bus)
        self._overlay.setup()

        # Initialize system tray
        self._setup_tray()

        # Register event handlers
        self._event_bus.on("audio.ready", self._on_audio_ready)

        # Setup hotkeys
        self._setup_hotkeys()

        # Start web dashboard (if enabled)
        self._setup_web_dashboard()

        logger.info("LinuxWhispr setup complete")

    def _create_stt_backend(self) -> STTBackend:
        """Create the STT backend based on config."""
        backend = self._config.stt.backend

        if backend == "faster-whisper":
            return FasterWhisperBackend(
                model_name=self._config.stt.model,
                device=self._config.stt.device,
                compute_type=self._config.stt.compute_type,
            )
        elif backend == "openai":
            from linux_whispr.stt.openai_api import OpenAIWhisperBackend

            # API key should come from secretstorage or env var
            import os

            api_key = os.environ.get("OPENAI_API_KEY", "")
            return OpenAIWhisperBackend(api_key=api_key)
        elif backend == "groq":
            from linux_whispr.stt.groq_api import GroqWhisperBackend

            import os

            api_key = os.environ.get("GROQ_API_KEY", "")
            return GroqWhisperBackend(api_key=api_key)
        else:
            logger.warning("Unknown STT backend '%s', falling back to faster-whisper", backend)
            return FasterWhisperBackend(model_name=self._config.stt.model)

    def _setup_ai_refinement(self) -> None:
        """Setup AI refinement pipeline if enabled."""
        if not self._config.ai.enabled or self._config.ai.backend == "none":
            return

        from linux_whispr.ai.refinement import RefinementPipeline

        llm_backend = self._create_llm_backend()
        if llm_backend is not None:
            self._refinement = RefinementPipeline(
                event_bus=self._event_bus,
                backend=llm_backend,
                enabled=True,
            )
            logger.info("AI refinement enabled (backend=%s)", self._config.ai.backend)

    def _create_llm_backend(self) -> object | None:
        """Create the LLM backend for AI refinement based on config."""
        import os

        backend = self._config.ai.backend

        if backend == "openai":
            from linux_whispr.ai.openai_llm import OpenAILLMBackend

            api_key = os.environ.get("OPENAI_API_KEY", "")
            model = self._config.ai.model or "gpt-4o-mini"
            return OpenAILLMBackend(api_key=api_key, model=model)
        elif backend == "groq":
            from linux_whispr.ai.groq_llm import GroqLLMBackend

            api_key = os.environ.get("GROQ_API_KEY", "")
            model = self._config.ai.model or "llama-3.1-8b-instant"
            return GroqLLMBackend(api_key=api_key, model=model)
        elif backend == "anthropic":
            from linux_whispr.ai.anthropic_llm import AnthropicLLMBackend

            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            model = self._config.ai.model or "claude-3-haiku-20240307"
            return AnthropicLLMBackend(api_key=api_key, model=model)
        elif backend == "local":
            from linux_whispr.ai.local_llm import LocalLLMBackend

            model_path = self._config.ai.model
            if model_path:
                return LocalLLMBackend(model_path=model_path)
            logger.warning("Local LLM backend requires a model path in config")
        else:
            logger.warning("Unknown AI backend: %s", backend)

        return None

    def _setup_web_dashboard(self) -> None:
        """Start the web dashboard server in a background thread."""
        if not self._config.web.enabled:
            logger.debug("Web dashboard disabled in config")
            return

        try:
            import uvicorn

            from linux_whispr.web.server import app as web_app
        except ImportError:
            logger.debug(
                "Web dashboard dependencies not installed (pip install linux-whispr[web])"
            )
            return

        port = self._config.web.port

        # Check if the port is already in use
        if self._is_port_in_use(port):
            logger.warning(
                "Port %d already in use — web dashboard will connect to existing instance",
                port,
            )
            if self._config.web.auto_open:
                import webbrowser

                url = f"http://127.0.0.1:{port}"
                logger.info("Opening existing web dashboard: %s", url)
                webbrowser.open(url)
            return

        config = uvicorn.Config(
            web_app, host="127.0.0.1", port=port, log_level="warning"
        )
        server = uvicorn.Server(config)
        self._web_server = server

        def _run_server() -> None:
            server.run()

        self._web_thread = threading.Thread(
            target=_run_server, daemon=True, name="web-dashboard"
        )
        self._web_thread.start()
        logger.info("Web dashboard starting on http://127.0.0.1:%d", port)

        if self._config.web.auto_open:
            def _wait_and_open_browser() -> None:
                import time
                import webbrowser

                url = f"http://127.0.0.1:{port}"
                # Poll until the server is actually accepting connections
                for _ in range(20):
                    time.sleep(0.5)
                    if self._is_port_in_use(port):
                        logger.info("Opening web dashboard: %s", url)
                        webbrowser.open(url)
                        return
                logger.warning("Web dashboard did not start in time, skipping browser open")

            threading.Thread(
                target=_wait_and_open_browser, daemon=True, name="browser-open"
            ).start()

    @staticmethod
    def _is_port_in_use(port: int) -> bool:
        """Check if a TCP port is already bound on localhost."""
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(("127.0.0.1", port)) == 0

    def _setup_tray(self) -> None:
        """Initialize the system tray icon."""
        try:
            from linux_whispr.ui.tray import SystemTray

            self._tray = SystemTray(
                event_bus=self._event_bus,
                on_toggle_dictation=self._on_dictation_hotkey,
                on_quit=self._request_quit,
            )
            self._tray.setup()
        except Exception:
            logger.debug("System tray initialization failed", exc_info=True)

    def _setup_hotkeys(self) -> None:
        """Register global hotkeys."""
        assert self._platform is not None

        listener = create_hotkey_listener(self._platform)
        listener.register(
            self._config.hotkey.dictation,
            self._on_dictation_hotkey,
            name="dictation",
        )
        self._hotkey_listener = listener

    def start(self) -> None:
        """Start the application (hotkey listener, tray)."""
        if self._hotkey_listener is not None:
            self._hotkey_listener.start()  # type: ignore[union-attr]

        if self._tray is not None:
            self._tray.start()  # type: ignore[union-attr]

        logger.info("LinuxWhispr started — press %s to dictate", self._config.hotkey.dictation)

    def stop(self) -> None:
        """Stop the application and clean up."""
        if self._hotkey_listener is not None:
            self._hotkey_listener.stop()  # type: ignore[union-attr]

        if self._audio is not None and self._audio.is_recording:
            self._audio.stop()

        if self._stt is not None and self._stt.is_loaded:
            self._stt.unload()

        if self._history is not None:
            self._history.close()

        if self._web_server is not None:
            self._web_server.should_exit = True  # type: ignore[union-attr]

        if self._tray is not None:
            self._tray.stop()  # type: ignore[union-attr]

        if self._overlay is not None:
            self._overlay.destroy()

        self._event_bus.clear()
        logger.info("LinuxWhispr stopped")

    def _request_quit(self) -> None:
        """Request application shutdown (from tray menu)."""
        import os
        import signal

        os.kill(os.getpid(), signal.SIGTERM)

    # --- Hotkey callbacks ---

    def _on_dictation_hotkey(self) -> None:
        """Handle dictation hotkey press (toggle mode)."""
        if self._state == AppState.IDLE:
            self._start_recording()
        elif self._state == AppState.RECORDING:
            self._stop_recording()
        else:
            logger.debug("Ignoring hotkey in state %s", self._state)

    def _start_recording(self) -> None:
        """Start audio recording."""
        assert self._audio is not None
        assert self._vad is not None

        self._set_state(AppState.RECORDING)
        self._vad.reset()
        self._audio.start()
        self._event_bus.emit("hotkey.dictation.start")

        # Start VAD monitoring thread
        self._vad_active = True
        self._vad_thread = threading.Thread(target=self._vad_monitor, daemon=True)
        self._vad_thread.start()

        logger.info("Recording started")

    def _stop_recording(self) -> None:
        """Stop audio recording and process."""
        assert self._audio is not None

        self._vad_active = False
        self._set_state(AppState.PROCESSING)
        self._event_bus.emit("hotkey.dictation.stop")

        # Stop recording returns WAV bytes and emits audio.ready
        wav_bytes = self._audio.stop()
        if wav_bytes is None:
            logger.warning("No audio captured")
            self._set_state(AppState.IDLE)

    def _on_audio_ready(self, wav_bytes: bytes, duration: float) -> None:
        """Handle audio ready event — run full STT + refinement pipeline."""
        # Run in a thread to avoid blocking the event bus
        threading.Thread(
            target=self._process_audio,
            args=(wav_bytes, duration),
            daemon=True,
            name="stt-pipeline",
        ).start()

    def _process_audio(self, wav_bytes: bytes, duration: float) -> None:
        """Full processing pipeline: STT → snippets → AI refinement → inject → history."""
        assert self._stt is not None
        assert self._injector is not None

        # Load STT model if not loaded
        if not self._stt.is_loaded:
            logger.info("Loading STT model (first use)...")
            self._event_bus.emit("stt.started")
            self._stt.load()

        # Transcribe
        self._event_bus.emit("stt.started")
        try:
            result = self._stt.transcribe(
                wav_bytes,
                language=self._config.stt.language,
                initial_prompt=self._get_dictionary_prompt(),
            )
        except Exception:
            logger.exception("Transcription failed")
            self._set_state(AppState.ERROR)
            from linux_whispr.platform.notifications import notify

            notify("Transcription Failed", "Check logs for details", urgency="critical")
            return

        if not result.text.strip():
            logger.info("Empty transcription, skipping injection")
            self._set_state(AppState.IDLE)
            return

        self._event_bus.emit("stt.complete", text=result.text, language=result.language)
        raw_text = result.text.strip()
        self._last_raw_text = raw_text
        self._last_duration = duration
        self._last_language = result.language
        logger.info("Transcribed: %s", raw_text[:100])

        # Snippet expansion (FR-11)
        final_text = raw_text
        refined_text: str | None = None
        success = False

        try:
            if self._snippets is not None:
                final_text = self._snippets.expand(final_text)
                if final_text != raw_text:
                    logger.info("Snippet expanded: %s", final_text[:100])

            # AI refinement (FR-4)
            if self._refinement is not None:
                app_name = self._get_active_window_name()
                dict_context = self._get_correction_context()
                from linux_whispr.ai.refinement import RefinementPipeline

                assert isinstance(self._refinement, RefinementPipeline)
                refined = self._refinement.refine(
                    raw_text=final_text,
                    app_name=app_name,
                    dictionary_context=dict_context,
                )
                if refined != final_text:
                    refined_text = refined
                    final_text = refined
                    logger.info("Refined: %s", final_text[:100])

            # Inject text (FR-6)
            success = self._injector.inject(final_text)
            if success:
                logger.info("Text injected (%d chars)", len(final_text))
            else:
                logger.error("Text injection failed")
        except Exception:
            logger.exception("Post-transcription pipeline failed")
        finally:
            # Save to history (FR-12) — always persist, even if injection failed
            if self._history is not None:
                try:
                    app_context = self._get_active_window_name()
                    self._history.add(
                        raw_text=raw_text,
                        refined_text=refined_text,
                        duration=duration,
                        app_context=app_context,
                        language=result.language,
                    )
                except Exception:
                    logger.exception("Failed to save transcription to history")

        # Start adaptive learning watch (FR-14)
        if self._adaptive is not None and success:
            self._adaptive.start_watching(final_text)

        self._set_state(AppState.IDLE)

    def _get_active_window_name(self) -> str | None:
        """Get the name of the currently active window."""
        assert self._platform is not None
        from linux_whispr.platform.detect import DisplayServer

        try:
            if self._platform.display_server == DisplayServer.X11:
                result = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            # Wayland: could use D-Bus or compositor IPC
            # For now, return None on Wayland
        except Exception:
            logger.debug("Failed to get active window name", exc_info=True)
        return None

    def _get_dictionary_prompt(self) -> str | None:
        """Build the initial_prompt from the custom dictionary (FR-10)."""
        if self._dictionary is not None:
            return self._dictionary.build_initial_prompt(
                promotion_threshold=self._config.adaptive.promotion_threshold
            )
        return None

    def _get_correction_context(self) -> str:
        """Build correction context string for AI refinement prompt (FR-14.8)."""
        if self._dictionary is None:
            return ""

        pairs = [
            f"{c.corrected} (not {c.heard})"
            for c in self._dictionary.corrections
            if c.count >= self._config.adaptive.promotion_threshold
        ]
        if not pairs:
            return ""
        return ", ".join(pairs)

    def _vad_monitor(self) -> None:
        """Monitor VAD in a separate thread to auto-stop on silence."""
        import time

        assert self._audio is not None
        assert self._vad is not None

        while self._vad_active and self._audio.is_recording:
            # Get latest audio frames for VAD processing
            if self._audio._frames:
                latest = self._audio._frames[-1]
                flat = latest.flatten() if latest.ndim > 1 else latest
                self._vad.is_speech(flat)

                if self._vad.should_stop():
                    logger.info("VAD: silence detected, auto-stopping")
                    self._event_bus.emit("audio.silence")
                    self._stop_recording()
                    return

            time.sleep(0.1)

    def _set_state(self, new_state: AppState) -> None:
        """Update application state and emit event."""
        old_state = self._state
        self._state = new_state
        self._event_bus.emit("state.change", old_state=old_state, new_state=new_state)
        logger.debug("State: %s → %s", old_state.name, new_state.name)
