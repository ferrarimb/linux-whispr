"""xdotool wrapper for X11 keystroke simulation and window queries."""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


def paste() -> bool:
    """Simulate Ctrl+V paste using xdotool."""
    try:
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
    except FileNotFoundError:
        logger.error("xdotool not found on PATH")
        return False
    except subprocess.TimeoutExpired:
        logger.error("xdotool paste timed out")
        return False


def type_text(text: str, delay_ms: int = 12) -> bool:
    """Type text character-by-character using xdotool (slower but more compatible)."""
    try:
        result = subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--delay", str(delay_ms), text],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("xdotool type failed: %s", result.stderr)
            return False
        return True
    except FileNotFoundError:
        logger.error("xdotool not found on PATH")
        return False
    except subprocess.TimeoutExpired:
        logger.error("xdotool type timed out")
        return False


def get_active_window_name() -> str | None:
    """Get the title of the currently active window."""
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def get_active_window_pid() -> int | None:
    """Get the PID of the currently active window."""
    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowpid"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass
    return None
