"""wtype wrapper for Wayland keystroke simulation."""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


def paste() -> bool:
    """Simulate Ctrl+V paste using wtype."""
    try:
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
    except FileNotFoundError:
        logger.error("wtype not found on PATH")
        return False
    except subprocess.TimeoutExpired:
        logger.error("wtype paste timed out")
        return False


def type_text(text: str) -> bool:
    """Type text directly using wtype (character-by-character)."""
    try:
        result = subprocess.run(
            ["wtype", text],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("wtype type failed: %s", result.stderr)
            return False
        return True
    except FileNotFoundError:
        logger.error("wtype not found on PATH")
        return False
    except subprocess.TimeoutExpired:
        logger.error("wtype type timed out")
        return False
