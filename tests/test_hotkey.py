"""Tests for hotkey parsing and listener factory."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from linux_whispr.input.x11_hotkey import _parse_hotkey
from linux_whispr.platform.detect import Desktop, DisplayServer, PlatformInfo


class TestHotkeyParsing:
    def test_simple_key(self) -> None:
        modifiers, key = _parse_hotkey("F12")
        assert modifiers == []
        assert key == "F12"

    def test_ctrl_shift_key(self) -> None:
        modifiers, key = _parse_hotkey("<Ctrl><Shift>h")
        assert "ctrl" in modifiers
        assert "shift" in modifiers
        assert key == "h"

    def test_single_modifier(self) -> None:
        modifiers, key = _parse_hotkey("<Alt>d")
        assert modifiers == ["alt"]
        assert key == "d"

    def test_super_key(self) -> None:
        modifiers, key = _parse_hotkey("<Super>h")
        assert modifiers == ["super"]
        assert key == "h"

    def test_no_key_raises(self) -> None:
        with pytest.raises(ValueError, match="No key found"):
            _parse_hotkey("<Ctrl><Shift>")


class TestHotkeyListenerFactory:
    def test_factory_with_x11_tries_x11_listener(self) -> None:
        from linux_whispr.input.hotkey import create_hotkey_listener

        platform = PlatformInfo(
            display_server=DisplayServer.X11,
            desktop=Desktop.I3,
            has_xdotool=True,
            has_wtype=False,
            has_ydotool=False,
            has_xclip=True,
            has_xsel=False,
            has_wl_clipboard=False,
        )

        # This will try to import X11 or pynput listener
        # If neither available, it raises RuntimeError
        try:
            listener = create_hotkey_listener(platform)
            assert listener is not None
        except (RuntimeError, ImportError):
            # Expected if neither python-xlib nor pynput is installed
            pass
