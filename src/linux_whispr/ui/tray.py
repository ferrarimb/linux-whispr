"""System tray icon using pystray (StatusNotifierItem / AppIndicator)."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from linux_whispr.app import AppState
    from linux_whispr.events import EventBus

logger = logging.getLogger(__name__)


class SystemTray:
    """System tray icon with context menu for quick actions.

    Uses pystray which supports:
    - StatusNotifierItem (SNI) on GNOME/KDE
    - AppIndicator on Ubuntu
    - XEmbed on older X11 environments
    """

    def __init__(
        self,
        event_bus: EventBus,
        on_toggle_dictation: Callable[[], None] | None = None,
        on_toggle_ai: Callable[[], None] | None = None,
        on_open_settings: Callable[[], None] | None = None,
        on_quit: Callable[[], None] | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._on_toggle_dictation = on_toggle_dictation
        self._on_toggle_ai = on_toggle_ai
        self._on_open_settings = on_open_settings
        self._on_quit = on_quit
        self._icon: object | None = None
        self._ai_enabled = False
        self._available = False

        try:
            import pystray
            self._available = True
        except ImportError:
            logger.warning("pystray not available — system tray disabled")

    def setup(self) -> None:
        """Create and configure the tray icon."""
        if not self._available:
            return

        import pystray
        from PIL import Image, ImageDraw

        # Create a simple icon (colored circle)
        image = self._create_icon_image("idle")

        menu = pystray.Menu(
            pystray.MenuItem(
                "Start Dictation",
                self._handle_toggle_dictation,
            ),
            pystray.MenuItem(
                lambda item: f"AI Refinement: {'ON' if self._ai_enabled else 'OFF'}",
                self._handle_toggle_ai,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Settings", self._handle_open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._handle_quit),
        )

        self._icon = pystray.Icon(
            name="linux-whispr",
            icon=image,
            title="LinuxWhispr",
            menu=menu,
        )

        # Register state change handler
        self._event_bus.on("state.change", self._on_state_change)

        logger.info("System tray icon created")

    def start(self) -> None:
        """Start the tray icon in a background thread."""
        if self._icon is None:
            return

        thread = threading.Thread(target=self._icon.run, daemon=True, name="tray")
        thread.start()
        logger.info("System tray running")

    def stop(self) -> None:
        """Stop and remove the tray icon."""
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass
            logger.info("System tray stopped")

    def _create_icon_image(self, state: str) -> object:
        """Create a PIL Image for the tray icon based on state."""
        from PIL import Image, ImageDraw

        size = 64
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        colors = {
            "idle": (128, 128, 128, 200),
            "recording": (220, 30, 30, 255),
            "processing": (50, 130, 255, 255),
            "done": (30, 200, 60, 255),
            "error": (255, 128, 0, 255),
        }
        color = colors.get(state, colors["idle"])

        # Draw a filled circle
        margin = 8
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=color,
        )

        return image

    def _update_icon(self, state: str) -> None:
        """Update the tray icon to reflect current state."""
        if self._icon is None:
            return

        try:
            self._icon.icon = self._create_icon_image(state)
        except Exception:
            logger.debug("Failed to update tray icon", exc_info=True)

    def _on_state_change(self, old_state: object = None, new_state: object = None, **kw: object) -> None:
        """Handle app state changes to update the tray icon."""
        from linux_whispr.app import AppState

        state_map = {
            AppState.IDLE: "idle",
            AppState.RECORDING: "recording",
            AppState.PROCESSING: "processing",
            AppState.ERROR: "error",
        }
        if isinstance(new_state, AppState):
            self._update_icon(state_map.get(new_state, "idle"))

    def _handle_toggle_dictation(self, icon: object = None, item: object = None) -> None:
        if self._on_toggle_dictation:
            self._on_toggle_dictation()

    def _handle_toggle_ai(self, icon: object = None, item: object = None) -> None:
        self._ai_enabled = not self._ai_enabled
        if self._on_toggle_ai:
            self._on_toggle_ai()

    def _handle_open_settings(self, icon: object = None, item: object = None) -> None:
        if self._on_open_settings:
            self._on_open_settings()

    def _handle_quit(self, icon: object = None, item: object = None) -> None:
        if self._on_quit:
            self._on_quit()
