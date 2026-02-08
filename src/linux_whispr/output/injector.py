"""Text injection orchestrator — clipboard + paste simulation."""

from __future__ import annotations

import logging
import subprocess
import time
from typing import TYPE_CHECKING

from linux_whispr.constants import CLIPBOARD_RESTORE_DELAY
from linux_whispr.output.clipboard import Clipboard

if TYPE_CHECKING:
    from linux_whispr.events import EventBus
    from linux_whispr.platform.detect import PlatformInfo

logger = logging.getLogger(__name__)


class TextInjector:
    """Injects text at the cursor position via clipboard + paste simulation.

    Pipeline:
    1. Save current clipboard contents
    2. Write new text to clipboard
    3. Simulate Ctrl+V paste
    4. Restore original clipboard after a delay
    """

    def __init__(
        self,
        event_bus: EventBus,
        platform: PlatformInfo,
        preserve_clipboard: bool = True,
        restore_delay: float = CLIPBOARD_RESTORE_DELAY,
        method: str = "auto",
    ) -> None:
        self._event_bus = event_bus
        self._platform = platform
        self._preserve_clipboard = preserve_clipboard
        self._restore_delay = restore_delay
        self._clipboard = Clipboard(platform)

        # Resolve injection method
        if method == "auto":
            self._method = platform.best_injection_tool
        else:
            self._method = method

        if self._method is None:
            logger.warning(
                "No text injection tool detected. Will copy to clipboard only."
            )

    def inject(self, text: str) -> bool:
        """Inject text at the current cursor position.

        Returns True on success, False on failure.
        """
        if not text:
            logger.warning("Empty text, nothing to inject")
            return False

        # Save original clipboard
        original_clipboard: str | None = None
        if self._preserve_clipboard:
            original_clipboard = self._clipboard.read()

        # Write text to clipboard
        if not self._clipboard.write(text):
            self._event_bus.emit("inject.error", error="Failed to write to clipboard")
            return False

        # Simulate paste
        success = self._simulate_paste()

        if not success:
            logger.warning("Paste simulation failed, text is in clipboard for manual paste")
            self._event_bus.emit("inject.error", error="Paste simulation failed")

        # Restore original clipboard after delay (in background to not block)
        if self._preserve_clipboard and original_clipboard is not None:
            import threading

            def _restore() -> None:
                time.sleep(self._restore_delay)
                self._clipboard.write(original_clipboard)

            threading.Thread(target=_restore, daemon=True).start()

        if success:
            self._event_bus.emit("inject.complete", text=text)

        return success

    def _simulate_paste(self) -> bool:
        """Simulate Ctrl+V using the best available tool."""
        if self._method is None:
            return False

        try:
            if self._method == "xdotool":
                return self._paste_xdotool()
            elif self._method == "wtype":
                return self._paste_wtype()
            elif self._method == "ydotool":
                return self._paste_ydotool()
            else:
                logger.error("Unknown injection method: %s", self._method)
                return False
        except Exception:
            logger.exception("Paste simulation failed with method '%s'", self._method)
            return False

    def _paste_xdotool(self) -> bool:
        """Simulate Ctrl+V using xdotool."""
        # Delay to ensure clipboard is ready (xclip needs time to serve)
        time.sleep(0.15)
        result = subprocess.run(
            ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            logger.error("xdotool paste failed: %s", result.stderr)
            return False
        return True

    def _paste_wtype(self) -> bool:
        """Simulate Ctrl+V using wtype."""
        time.sleep(0.05)
        result = subprocess.run(
            ["wtype", "-M", "ctrl", "-k", "v", "-m", "ctrl"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            logger.error("wtype paste failed: %s", result.stderr)
            return False
        return True

    def _paste_ydotool(self) -> bool:
        """Simulate Ctrl+V using ydotool."""
        time.sleep(0.05)
        result = subprocess.run(
            ["ydotool", "key", "29:1", "47:1", "47:0", "29:0"],  # Ctrl+V keycodes
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            logger.error("ydotool paste failed: %s", result.stderr)
            return False
        return True
