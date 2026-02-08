"""Detect display server, desktop environment, and available tools."""

from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DisplayServer(Enum):
    """Display server type."""

    X11 = "x11"
    WAYLAND = "wayland"
    UNKNOWN = "unknown"


class Desktop(Enum):
    """Desktop environment / compositor."""

    GNOME = "gnome"
    KDE = "kde"
    SWAY = "sway"
    HYPRLAND = "hyprland"
    I3 = "i3"
    XFCE = "xfce"
    OTHER = "other"


@dataclass(frozen=True)
class PlatformInfo:
    """Detected platform capabilities."""

    display_server: DisplayServer
    desktop: Desktop

    # Available text injection tools
    has_xdotool: bool
    has_wtype: bool
    has_ydotool: bool

    # Available clipboard tools
    has_xclip: bool
    has_xsel: bool
    has_wl_clipboard: bool

    @property
    def best_injection_tool(self) -> str | None:
        """Return the best available text injection tool for this platform."""
        if self.display_server == DisplayServer.WAYLAND:
            if self.has_wtype:
                return "wtype"
            if self.has_ydotool:
                return "ydotool"
            # Fallback to xdotool under XWayland
            if self.has_xdotool:
                return "xdotool"
        else:
            if self.has_xdotool:
                return "xdotool"
        return None

    @property
    def best_clipboard_tool(self) -> str | None:
        """Return the best available clipboard tool for this platform."""
        if self.display_server == DisplayServer.WAYLAND:
            if self.has_wl_clipboard:
                return "wl-clipboard"
            # Fallback to xclip under XWayland
            if self.has_xclip:
                return "xclip"
            if self.has_xsel:
                return "xsel"
        else:
            if self.has_xclip:
                return "xclip"
            if self.has_xsel:
                return "xsel"
        return None


def _detect_display_server() -> DisplayServer:
    """Detect the display server from environment variables."""
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type == "wayland":
        return DisplayServer.WAYLAND
    if session_type == "x11":
        return DisplayServer.X11

    # Fallback: check for WAYLAND_DISPLAY
    if os.environ.get("WAYLAND_DISPLAY"):
        return DisplayServer.WAYLAND
    if os.environ.get("DISPLAY"):
        return DisplayServer.X11

    return DisplayServer.UNKNOWN


def _detect_desktop() -> Desktop:
    """Detect the desktop environment / compositor."""
    current_desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()

    if "gnome" in current_desktop:
        return Desktop.GNOME
    if "kde" in current_desktop or "plasma" in current_desktop:
        return Desktop.KDE
    if "sway" in current_desktop:
        return Desktop.SWAY
    if "hyprland" in current_desktop:
        return Desktop.HYPRLAND
    if "xfce" in current_desktop:
        return Desktop.XFCE
    if "i3" in current_desktop:
        return Desktop.I3

    # Check DESKTOP_SESSION as fallback
    session = os.environ.get("DESKTOP_SESSION", "").lower()
    if "gnome" in session:
        return Desktop.GNOME
    if "plasma" in session or "kde" in session:
        return Desktop.KDE
    if "i3" in session:
        return Desktop.I3

    return Desktop.OTHER


def _has_tool(name: str) -> bool:
    """Check if a command-line tool is available on PATH."""
    return shutil.which(name) is not None


def detect_platform() -> PlatformInfo:
    """Detect the full platform capabilities."""
    display_server = _detect_display_server()
    desktop = _detect_desktop()

    info = PlatformInfo(
        display_server=display_server,
        desktop=desktop,
        has_xdotool=_has_tool("xdotool"),
        has_wtype=_has_tool("wtype"),
        has_ydotool=_has_tool("ydotool"),
        has_xclip=_has_tool("xclip"),
        has_xsel=_has_tool("xsel"),
        has_wl_clipboard=_has_tool("wl-copy"),
    )

    logger.info(
        "Platform detected: display=%s, desktop=%s, injection=%s, clipboard=%s",
        info.display_server.value,
        info.desktop.value,
        info.best_injection_tool or "none",
        info.best_clipboard_tool or "none",
    )
    return info
