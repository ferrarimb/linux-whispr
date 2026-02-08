"""Manage autostart via XDG autostart desktop entry."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from linux_whispr.constants import APP_NAME

logger = logging.getLogger(__name__)

AUTOSTART_DIR = Path.home() / ".config" / "autostart"
DESKTOP_ENTRY_NAME = f"{APP_NAME}.desktop"

DESKTOP_ENTRY_CONTENT = f"""\
[Desktop Entry]
Type=Application
Name=LinuxWhispr
Comment=Privacy-first voice dictation for Linux
Exec=linux-whispr
Icon=linux-whispr
Terminal=false
Categories=Utility;Accessibility;
StartupNotify=false
X-GNOME-Autostart-enabled=true
"""


def enable_autostart() -> None:
    """Install an XDG autostart desktop entry."""
    AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
    entry_path = AUTOSTART_DIR / DESKTOP_ENTRY_NAME
    entry_path.write_text(DESKTOP_ENTRY_CONTENT)
    logger.info("Autostart enabled: %s", entry_path)


def disable_autostart() -> None:
    """Remove the XDG autostart desktop entry."""
    entry_path = AUTOSTART_DIR / DESKTOP_ENTRY_NAME
    if entry_path.exists():
        entry_path.unlink()
        logger.info("Autostart disabled: removed %s", entry_path)
    else:
        logger.debug("Autostart entry not found at %s", entry_path)


def is_autostart_enabled() -> bool:
    """Check if autostart is currently enabled."""
    return (AUTOSTART_DIR / DESKTOP_ENTRY_NAME).exists()
