"""Settings window (GTK4 + libadwaita)."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from linux_whispr.config import AppConfig
    from linux_whispr.events import EventBus
    from linux_whispr.features.dictionary import Dictionary
    from linux_whispr.features.history import HistoryManager
    from linux_whispr.features.snippets import SnippetEngine
    from linux_whispr.stt.model_manager import ModelManager

logger = logging.getLogger(__name__)


class SettingsWindow:
    """GTK4 + libadwaita settings window.

    Sections (FR-9.3):
    - General: hotkey bindings, activation mode, auto-start
    - Audio: input device, silence detection, max duration
    - Transcription: STT backend, model selection, language, model management
    - AI Refinement: enable/disable, backend, API keys, custom prompts
    - Text Injection: method preference, clipboard preservation
    - Custom Dictionary: add/remove words and terms
    - Snippets: manage trigger → expansion mappings
    - History: browse/search/delete transcriptions
    - Appearance: overlay position, theme
    - Privacy: data retention, audio deletion
    """

    def __init__(
        self,
        config: AppConfig,
        event_bus: EventBus,
        dictionary: Dictionary | None = None,
        snippets: SnippetEngine | None = None,
        history: HistoryManager | None = None,
        model_manager: ModelManager | None = None,
    ) -> None:
        self._config = config
        self._event_bus = event_bus
        self._dictionary = dictionary
        self._snippets = snippets
        self._history = history
        self._model_manager = model_manager
        self._window: object | None = None
        self._gtk_available = False

        try:
            import gi

            gi.require_version("Gtk", "4.0")
            gi.require_version("Adw", "1")
            self._gtk_available = True
        except (ImportError, ValueError):
            logger.warning("GTK4/libadwaita not available — settings UI disabled")

    def show(self) -> None:
        """Show the settings window."""
        if not self._gtk_available:
            logger.warning("Cannot show settings: GTK4 not available")
            return

        if self._window is not None:
            from gi.repository import GLib

            GLib.idle_add(self._window.present)
            return

        self._build_window()
        if self._window is not None:
            from gi.repository import GLib

            GLib.idle_add(self._window.present)

    def _build_window(self) -> None:
        """Build the settings window with all pages."""
        import gi

        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw, Gtk

        self._window = Adw.PreferencesWindow(
            title="LinuxWhispr Settings",
            default_width=700,
            default_height=600,
        )
        self._window.connect("close-request", self._on_close)

        # General page
        self._window.add(self._build_general_page())

        # Audio page
        self._window.add(self._build_audio_page())

        # Transcription page
        self._window.add(self._build_transcription_page())

        # AI page
        self._window.add(self._build_ai_page())

        # Dictionary page
        self._window.add(self._build_dictionary_page())

        # History page
        self._window.add(self._build_history_page())

    def _build_general_page(self) -> object:
        """Build the General settings page."""
        from gi.repository import Adw, Gtk

        page = Adw.PreferencesPage(title="General", icon_name="preferences-system-symbolic")

        # Hotkeys group
        hotkey_group = Adw.PreferencesGroup(title="Hotkeys")

        dictation_row = Adw.EntryRow(title="Dictation Hotkey")
        dictation_row.set_text(self._config.hotkey.dictation)
        dictation_row.connect("changed", lambda r: self._update_config("hotkey", "dictation", r.get_text()))
        hotkey_group.add(dictation_row)

        command_row = Adw.EntryRow(title="Command Mode Hotkey")
        command_row.set_text(self._config.hotkey.command)
        command_row.connect("changed", lambda r: self._update_config("hotkey", "command", r.get_text()))
        hotkey_group.add(command_row)

        # Activation mode
        mode_row = Adw.ComboRow(title="Activation Mode", subtitle="How the dictation hotkey works")
        mode_model = Gtk.StringList.new(["Toggle", "Push-to-Talk"])
        mode_row.set_model(mode_model)
        mode_row.set_selected(0 if self._config.hotkey.mode == "toggle" else 1)
        mode_row.connect("notify::selected", lambda r, _: self._update_config(
            "hotkey", "mode", "toggle" if r.get_selected() == 0 else "push-to-talk"
        ))
        hotkey_group.add(mode_row)

        page.add(hotkey_group)

        # Startup group
        startup_group = Adw.PreferencesGroup(title="Startup")

        autostart_row = Adw.SwitchRow(title="Start on Login", subtitle="Launch LinuxWhispr automatically")
        autostart_row.set_active(self._config.autostart)
        autostart_row.connect("notify::active", lambda r, _: self._toggle_autostart(r.get_active()))
        startup_group.add(autostart_row)

        page.add(startup_group)
        return page

    def _build_audio_page(self) -> object:
        """Build the Audio settings page."""
        from gi.repository import Adw, Gtk

        page = Adw.PreferencesPage(title="Audio", icon_name="audio-input-microphone-symbolic")

        group = Adw.PreferencesGroup(title="Recording")

        # Silence duration
        silence_row = Adw.SpinRow.new_with_range(0.5, 10.0, 0.5)
        silence_row.set_title("Silence Duration (seconds)")
        silence_row.set_subtitle("Auto-stop after this much silence")
        silence_row.set_value(self._config.audio.silence_duration)
        silence_row.connect("notify::value", lambda r, _: self._update_config(
            "audio", "silence_duration", r.get_value()
        ))
        group.add(silence_row)

        # VAD threshold
        threshold_row = Adw.SpinRow.new_with_range(0.1, 0.9, 0.05)
        threshold_row.set_title("VAD Sensitivity")
        threshold_row.set_subtitle("Lower = more sensitive to speech")
        threshold_row.set_value(self._config.audio.silence_threshold)
        threshold_row.connect("notify::value", lambda r, _: self._update_config(
            "audio", "silence_threshold", r.get_value()
        ))
        group.add(threshold_row)

        # Whisper mode
        whisper_row = Adw.SwitchRow(title="Whisper Mode", subtitle="Boost microphone gain for quiet environments")
        whisper_row.set_active(self._config.audio.whisper_mode)
        whisper_row.connect("notify::active", lambda r, _: self._update_config(
            "audio", "whisper_mode", r.get_active()
        ))
        group.add(whisper_row)

        page.add(group)
        return page

    def _build_transcription_page(self) -> object:
        """Build the Transcription settings page."""
        from gi.repository import Adw, Gtk

        page = Adw.PreferencesPage(title="Transcription", icon_name="document-edit-symbolic")

        group = Adw.PreferencesGroup(title="Speech-to-Text Engine")

        # Backend selection
        backend_row = Adw.ComboRow(title="STT Backend")
        backends = Gtk.StringList.new(["faster-whisper (Local)", "OpenAI Whisper API", "Groq Whisper API"])
        backend_row.set_model(backends)
        backend_map = {"faster-whisper": 0, "openai": 1, "groq": 2}
        backend_row.set_selected(backend_map.get(self._config.stt.backend, 0))
        group.add(backend_row)

        # Model selection
        model_row = Adw.ComboRow(title="Whisper Model", subtitle="Larger models are more accurate but slower")
        from linux_whispr.constants import SUPPORTED_WHISPER_MODELS

        models = Gtk.StringList.new(SUPPORTED_WHISPER_MODELS)
        model_row.set_model(models)
        try:
            model_idx = SUPPORTED_WHISPER_MODELS.index(self._config.stt.model)
        except ValueError:
            model_idx = 0
        model_row.set_selected(model_idx)
        model_row.connect("notify::selected", lambda r, _: self._update_config(
            "stt", "model", SUPPORTED_WHISPER_MODELS[r.get_selected()]
        ))
        group.add(model_row)

        # Device
        device_row = Adw.ComboRow(title="Compute Device")
        devices = Gtk.StringList.new(["Auto", "CPU", "CUDA (GPU)"])
        device_row.set_model(devices)
        device_map = {"auto": 0, "cpu": 1, "cuda": 2}
        device_row.set_selected(device_map.get(self._config.stt.device, 0))
        group.add(device_row)

        page.add(group)
        return page

    def _build_ai_page(self) -> object:
        """Build the AI Refinement settings page."""
        from gi.repository import Adw, Gtk

        page = Adw.PreferencesPage(title="AI Refinement", icon_name="starred-symbolic")

        group = Adw.PreferencesGroup(title="Text Refinement")

        # Enable/disable
        enable_row = Adw.SwitchRow(
            title="Enable AI Refinement",
            subtitle="Clean up filler words, fix grammar, format by context",
        )
        enable_row.set_active(self._config.ai.enabled)
        enable_row.connect("notify::active", lambda r, _: self._update_config(
            "ai", "enabled", r.get_active()
        ))
        group.add(enable_row)

        # Backend selection
        backend_row = Adw.ComboRow(title="LLM Backend")
        backends = Gtk.StringList.new(["None", "OpenAI", "Groq", "Anthropic", "Local (llama.cpp)"])
        backend_row.set_model(backends)
        ai_backend_map = {"none": 0, "openai": 1, "groq": 2, "anthropic": 3, "local": 4}
        backend_row.set_selected(ai_backend_map.get(self._config.ai.backend, 0))
        group.add(backend_row)

        page.add(group)

        # Custom prompt group
        prompt_group = Adw.PreferencesGroup(title="Custom System Prompt")
        prompt_row = Adw.EntryRow(title="Override default refinement prompt")
        if self._config.ai.custom_prompt:
            prompt_row.set_text(self._config.ai.custom_prompt)
        prompt_group.add(prompt_row)
        page.add(prompt_group)

        return page

    def _build_dictionary_page(self) -> object:
        """Build the Dictionary & Snippets settings page."""
        from gi.repository import Adw, Gtk

        page = Adw.PreferencesPage(title="Dictionary", icon_name="accessories-dictionary-symbolic")

        # Custom words group
        dict_group = Adw.PreferencesGroup(
            title="Custom Words",
            description="Words added here improve recognition accuracy",
        )

        if self._dictionary is not None:
            for entry in self._dictionary.entries:
                row = Adw.ActionRow(title=entry.word, subtitle=f"{entry.source} · {entry.category}")
                dict_group.add(row)

        # Add word button
        add_row = Adw.EntryRow(title="Add new word")
        add_row.connect("apply", self._on_add_dictionary_word)
        dict_group.add(add_row)

        page.add(dict_group)

        # Snippets group
        snippet_group = Adw.PreferencesGroup(
            title="Voice Snippets",
            description="Trigger phrases that expand to longer text",
        )

        if self._snippets is not None:
            for snippet in self._snippets.snippets:
                row = Adw.ActionRow(title=snippet.trigger, subtitle=snippet.expansion)
                snippet_group.add(row)

        page.add(snippet_group)

        # Learned corrections group
        corrections_group = Adw.PreferencesGroup(
            title="Learned Corrections",
            description="Automatically learned from your edits",
        )

        if self._dictionary is not None:
            for corr in self._dictionary.corrections:
                row = Adw.ActionRow(
                    title=f"{corr.heard} → {corr.corrected}",
                    subtitle=f"Seen {corr.count} time(s)",
                )
                corrections_group.add(row)

        page.add(corrections_group)
        return page

    def _build_history_page(self) -> object:
        """Build the History settings page."""
        from gi.repository import Adw, Gtk

        page = Adw.PreferencesPage(title="History", icon_name="document-open-recent-symbolic")

        group = Adw.PreferencesGroup(title="Transcription History")

        # Retention
        retention_row = Adw.SpinRow.new_with_range(1, 365, 1)
        retention_row.set_title("Retention (days)")
        retention_row.set_subtitle("Auto-delete entries older than this")
        retention_row.set_value(self._config.history.retention_days)
        group.add(retention_row)

        # Show recent entries
        if self._history is not None:
            recent = self._history.get_recent(limit=10)
            for entry in recent:
                text_preview = entry.raw_text[:80] + ("..." if len(entry.raw_text) > 80 else "")
                row = Adw.ActionRow(
                    title=text_preview,
                    subtitle=f"{entry.timestamp[:16]} · {entry.word_count} words · {entry.app_context or 'unknown'}",
                )
                group.add(row)

        page.add(group)

        # Actions group
        actions_group = Adw.PreferencesGroup(title="Actions")

        clear_button = Gtk.Button(label="Clear All History")
        clear_button.add_css_class("destructive-action")
        clear_button.connect("clicked", self._on_clear_history)
        actions_group.add(clear_button)

        page.add(actions_group)
        return page

    def _update_config(self, section: str, key: str, value: object) -> None:
        """Update a config value and save."""
        sub = getattr(self._config, section)
        setattr(sub, key, value)
        self._config.save()
        logger.debug("Config updated: %s.%s = %s", section, key, value)

    def _toggle_autostart(self, enabled: bool) -> None:
        """Toggle autostart and update config."""
        from linux_whispr.platform.autostart import disable_autostart, enable_autostart

        if enabled:
            enable_autostart()
        else:
            disable_autostart()
        self._config.autostart = enabled
        self._config.save()

    def _on_add_dictionary_word(self, row: object) -> None:
        """Handle adding a new dictionary word."""
        word = row.get_text().strip()  # type: ignore[union-attr]
        if word and self._dictionary is not None:
            self._dictionary.add_word(word)
            self._dictionary.save()
            row.set_text("")  # type: ignore[union-attr]
            logger.info("Added dictionary word: %s", word)

    def _on_clear_history(self, button: object) -> None:
        """Handle clear all history button."""
        if self._history is not None:
            count = self._history.clear()
            logger.info("Cleared %d history entries", count)

    def _on_close(self, window: object) -> bool:
        """Handle window close."""
        self._window = None
        return False  # Allow default close behavior
