"""First-run setup wizard (GTK4 + libadwaita)."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from linux_whispr.config import AppConfig
    from linux_whispr.events import EventBus

logger = logging.getLogger(__name__)


class SetupWizard:
    """First-run wizard that guides users through initial configuration.

    Steps (FR-9.4):
    1. Welcome screen
    2. Microphone test (audio level confirmation)
    3. Model selection (with size/speed trade-offs)
    4. Model download (progress bar)
    5. Hotkey configuration
    6. Quick test (dictate and see result)
    """

    def __init__(self, config: AppConfig, event_bus: EventBus) -> None:
        self._config = config
        self._event_bus = event_bus
        self._window: object | None = None
        self._gtk_available = False
        self._completed = False

        try:
            import gi

            gi.require_version("Gtk", "4.0")
            gi.require_version("Adw", "1")
            self._gtk_available = True
        except (ImportError, ValueError):
            logger.warning("GTK4/libadwaita not available — wizard will run in CLI mode")

    @property
    def completed(self) -> bool:
        return self._completed

    def run(self) -> bool:
        """Run the setup wizard. Returns True if completed successfully."""
        if self._gtk_available:
            return self._run_gtk()
        return self._run_cli()

    def _run_cli(self) -> bool:
        """CLI-based first-run setup (fallback when GTK4 is unavailable)."""
        from rich.console import Console
        from rich.panel import Panel
        from rich.prompt import Confirm, Prompt

        console = Console()

        # Welcome
        console.print(Panel(
            "[bold]Welcome to LinuxWhispr![/bold]\n\n"
            "Privacy-first voice dictation for Linux.\n"
            "Let's set up your system for voice dictation.",
            title="LinuxWhispr Setup",
            border_style="blue",
        ))

        # Model selection
        console.print("\n[bold]Step 1: Choose a Whisper model[/bold]\n")
        console.print("  [cyan]tiny[/cyan]    — ~75MB,  fastest, lowest accuracy")
        console.print("  [cyan]base[/cyan]    — ~150MB, good balance (recommended for CPU)")
        console.print("  [cyan]small[/cyan]   — ~500MB, better accuracy")
        console.print("  [cyan]medium[/cyan]  — ~1.5GB, high accuracy")
        console.print("  [cyan]large-v3-turbo[/cyan] — ~1.6GB, best speed/accuracy (needs GPU)")
        console.print()

        model = Prompt.ask(
            "Select model",
            choices=["tiny", "base", "small", "medium", "large-v3-turbo"],
            default="base",
        )
        self._config.stt.model = model

        # Hotkey
        console.print("\n[bold]Step 2: Hotkey configuration[/bold]\n")
        console.print(f"  Current dictation hotkey: [cyan]{self._config.hotkey.dictation}[/cyan]")
        if Confirm.ask("Keep default hotkey?", default=True):
            pass
        else:
            hotkey = Prompt.ask("Enter hotkey (e.g., F12, F8, <Ctrl><Shift>d)", default="F12")
            self._config.hotkey.dictation = hotkey

        # Download model
        console.print(f"\n[bold]Step 3: Download model '{model}'[/bold]\n")
        if Confirm.ask("Download now?", default=True):
            console.print(f"Downloading [cyan]{model}[/cyan]... (this may take a while)")
            try:
                from linux_whispr.stt.model_manager import ModelManager

                mm = ModelManager()
                mm.download(model)
                console.print("[green]✓ Model downloaded successfully![/green]")
            except Exception as e:
                console.print(f"[yellow]⚠ Download failed: {e}[/yellow]")
                console.print("  The model will be downloaded on first use.")

        # Audio test
        console.print("\n[bold]Step 4: Microphone test[/bold]\n")
        if Confirm.ask("Test your microphone?", default=True):
            self._cli_mic_test(console)

        # Save config
        self._config.first_run = False
        self._config.save()
        self._completed = True

        console.print(Panel(
            f"[bold green]Setup complete![/bold green]\n\n"
            f"Press [cyan]{self._config.hotkey.dictation}[/cyan] to start dictating.\n"
            f"Model: [cyan]{self._config.stt.model}[/cyan]\n\n"
            f"LinuxWhispr is now running in the background.",
            title="Ready",
            border_style="green",
        ))

        return True

    def _cli_mic_test(self, console: object) -> None:
        """Quick CLI microphone test."""
        try:
            import time

            import numpy as np
            import sounddevice as sd

            from linux_whispr.constants import AUDIO_CHANNELS, AUDIO_SAMPLE_RATE

            console.print("  Recording 3 seconds... speak now!")  # type: ignore[union-attr]

            audio = sd.rec(
                int(3 * AUDIO_SAMPLE_RATE),
                samplerate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype="int16",
            )
            sd.wait()

            rms = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
            level = min(1.0, rms / 32768.0 * 10.0)

            if level > 0.01:
                bars = "█" * int(level * 20) + "░" * (20 - int(level * 20))
                console.print(f"  Audio level: [{bars}] {level:.2f}")  # type: ignore[union-attr]
                console.print("  [green]✓ Microphone is working![/green]")  # type: ignore[union-attr]
            else:
                console.print("  [yellow]⚠ Very low audio level. Check your microphone.[/yellow]")  # type: ignore[union-attr]

        except Exception as e:
            console.print(f"  [yellow]⚠ Mic test failed: {e}[/yellow]")  # type: ignore[union-attr]

    def _run_gtk(self) -> bool:
        """GTK4-based first-run setup wizard."""
        import gi

        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Adw, Gtk

        app = Adw.Application(application_id="com.github.linux-whispr.wizard")

        def on_activate(app: Adw.Application) -> None:
            window = Adw.Window(
                title="LinuxWhispr Setup",
                default_width=500,
                default_height=400,
                application=app,
            )

            # Use a Carousel for wizard pages
            carousel = Adw.Carousel(
                hexpand=True,
                vexpand=True,
                allow_long_swipes=False,
            )

            # Page 1: Welcome
            welcome = self._build_welcome_page()
            carousel.append(welcome)

            # Page 2: Model selection
            model_page = self._build_model_page()
            carousel.append(model_page)

            # Page 3: Hotkey
            hotkey_page = self._build_hotkey_page()
            carousel.append(hotkey_page)

            # Page indicator
            indicator = Adw.CarouselIndicatorDots(carousel=carousel)

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            box.append(carousel)
            box.append(indicator)

            window.set_content(box)
            window.present()

        app.connect("activate", on_activate)
        app.run(None)

        return self._completed

    def _build_welcome_page(self) -> object:
        """Build the welcome page widget."""
        from gi.repository import Adw, Gtk

        page = Adw.StatusPage(
            title="Welcome to LinuxWhispr",
            description=(
                "Privacy-first voice dictation for Linux.\n\n"
                "Let's get you set up in just a few steps."
            ),
            icon_name="audio-input-microphone-symbolic",
        )
        return page

    def _build_model_page(self) -> object:
        """Build the model selection page widget."""
        from gi.repository import Adw, Gtk

        page = Adw.StatusPage(
            title="Choose a Model",
            description="Select a Whisper model for speech recognition.",
        )

        group = Adw.PreferencesGroup()

        from linux_whispr.constants import SUPPORTED_WHISPER_MODELS
        from linux_whispr.stt.model_manager import MODEL_SIZES

        model_row = Adw.ComboRow(title="Whisper Model")
        labels = []
        for m in SUPPORTED_WHISPER_MODELS:
            size = MODEL_SIZES.get(m, 0)
            labels.append(f"{m} (~{size}MB)")
        model_list = Gtk.StringList.new(labels)
        model_row.set_model(model_list)
        model_row.set_selected(1)  # default to "base"
        group.add(model_row)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.append(page)
        box.append(group)
        return box

    def _build_hotkey_page(self) -> object:
        """Build the hotkey configuration page widget."""
        from gi.repository import Adw, Gtk

        page = Adw.StatusPage(
            title="Configure Hotkey",
            description=f"Current: {self._config.hotkey.dictation}\nPress this key anywhere to start dictating.",
        )

        group = Adw.PreferencesGroup()
        hotkey_row = Adw.EntryRow(title="Dictation Hotkey")
        hotkey_row.set_text(self._config.hotkey.dictation)
        group.add(hotkey_row)

        # Done button
        done_button = Gtk.Button(label="Start Using LinuxWhispr")
        done_button.add_css_class("suggested-action")
        done_button.connect("clicked", self._on_wizard_complete)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.append(page)
        box.append(group)
        box.append(done_button)
        return box

    def _on_wizard_complete(self, button: object) -> None:
        """Handle wizard completion."""
        self._config.first_run = False
        self._config.save()
        self._completed = True
        logger.info("Setup wizard completed")

        if self._window is not None:
            self._window.close()  # type: ignore[union-attr]
