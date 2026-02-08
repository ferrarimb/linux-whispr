"""Tests for platform detection."""

from __future__ import annotations

import os
from unittest.mock import patch

from linux_whispr.platform.detect import (
    Desktop,
    DisplayServer,
    _detect_desktop,
    _detect_display_server,
)


class TestDisplayServerDetection:
    def test_wayland_from_session_type(self) -> None:
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}, clear=False):
            assert _detect_display_server() == DisplayServer.WAYLAND

    def test_x11_from_session_type(self) -> None:
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}, clear=False):
            assert _detect_display_server() == DisplayServer.X11

    def test_wayland_from_display_env(self) -> None:
        env = {"XDG_SESSION_TYPE": "", "WAYLAND_DISPLAY": "wayland-0"}
        with patch.dict(os.environ, env, clear=False):
            assert _detect_display_server() == DisplayServer.WAYLAND

    def test_x11_from_display_env(self) -> None:
        env = {"XDG_SESSION_TYPE": "", "WAYLAND_DISPLAY": "", "DISPLAY": ":0"}
        with patch.dict(os.environ, env, clear=False):
            assert _detect_display_server() == DisplayServer.X11


class TestDesktopDetection:
    def test_gnome(self) -> None:
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "GNOME"}, clear=False):
            assert _detect_desktop() == Desktop.GNOME

    def test_kde(self) -> None:
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"}, clear=False):
            assert _detect_desktop() == Desktop.KDE

    def test_sway(self) -> None:
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "sway"}, clear=False):
            assert _detect_desktop() == Desktop.SWAY

    def test_hyprland(self) -> None:
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "Hyprland"}, clear=False):
            assert _detect_desktop() == Desktop.HYPRLAND

    def test_i3(self) -> None:
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "i3"}, clear=False):
            assert _detect_desktop() == Desktop.I3
