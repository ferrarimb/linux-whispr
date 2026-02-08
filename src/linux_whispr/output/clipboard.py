"""Clipboard operations for X11 (xclip/xsel) and Wayland (wl-clipboard)."""

from __future__ import annotations

import logging
import subprocess
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from linux_whispr.platform.detect import PlatformInfo

logger = logging.getLogger(__name__)


class Clipboard:
    """Cross-platform clipboard read/write using system tools."""

    def __init__(self, platform: PlatformInfo) -> None:
        self._platform = platform
        self._tool = platform.best_clipboard_tool

        if self._tool is None:
            logger.warning("No clipboard tool detected! Clipboard operations will fail.")

    def read(self) -> str | None:
        """Read current clipboard contents. Returns None on failure."""
        try:
            if self._tool == "wl-clipboard":
                result = subprocess.run(
                    ["wl-paste", "--no-newline"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            elif self._tool == "xclip":
                result = subprocess.run(
                    ["xclip", "-selection", "clipboard", "-o"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            elif self._tool == "xsel":
                result = subprocess.run(
                    ["xsel", "--clipboard", "--output"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            else:
                logger.error("No clipboard tool available")
                return None

            if result.returncode != 0:
                # Empty clipboard is not an error
                if "nothing is copied" in result.stderr.lower() or result.returncode == 1:
                    return ""
                logger.error("Clipboard read failed: %s", result.stderr)
                return None

            return result.stdout
        except subprocess.TimeoutExpired:
            logger.error("Clipboard read timed out")
            return None
        except Exception:
            logger.exception("Clipboard read failed")
            return None

    def write(self, text: str) -> bool:
        """Write text to the clipboard. Returns True on success."""
        try:
            if self._tool == "wl-clipboard":
                result = subprocess.run(
                    ["wl-copy"],
                    input=text,
                    text=True,
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    logger.error("Clipboard write failed: %s", result.stderr)
                    return False
            elif self._tool == "xclip":
                # xclip stays alive to serve clipboard requests, so
                # communicate()/wait() will block until another app
                # reads the clipboard. Write to stdin and let it run.
                proc = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if proc.stdin:
                    proc.stdin.write(text.encode())
                    proc.stdin.close()
                # Brief pause to let xclip read the input
                time.sleep(0.05)
            elif self._tool == "xsel":
                result = subprocess.run(
                    ["xsel", "--clipboard", "--input"],
                    input=text,
                    text=True,
                    capture_output=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    logger.error("Clipboard write failed: %s", result.stderr)
                    return False
            else:
                logger.error("No clipboard tool available")
                return False

            return True
        except subprocess.TimeoutExpired:
            logger.error("Clipboard write timed out")
            return False
        except Exception:
            logger.exception("Clipboard write failed")
            return False
