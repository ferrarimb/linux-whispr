"""ydotool wrapper for universal Wayland keystroke simulation (requires uinput)."""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)

# ydotool uses Linux input event keycodes
# Ctrl = 29, V = 47
KEY_CTRL = 29
KEY_V = 47


def paste() -> bool:
    """Simulate Ctrl+V paste using ydotool."""
    try:
        # ydotool key format: keycode:state (1=press, 0=release)
        result = subprocess.run(
            [
                "ydotool", "key",
                f"{KEY_CTRL}:1", f"{KEY_V}:1",
                f"{KEY_V}:0", f"{KEY_CTRL}:0",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            logger.error("ydotool paste failed: %s", result.stderr)
            return False
        return True
    except FileNotFoundError:
        logger.error("ydotool not found on PATH")
        return False
    except subprocess.TimeoutExpired:
        logger.error("ydotool paste timed out")
        return False


def type_text(text: str) -> bool:
    """Type text using ydotool."""
    try:
        result = subprocess.run(
            ["ydotool", "type", "--", text],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("ydotool type failed: %s", result.stderr)
            return False
        return True
    except FileNotFoundError:
        logger.error("ydotool not found on PATH")
        return False
    except subprocess.TimeoutExpired:
        logger.error("ydotool type timed out")
        return False
