"""Tests for text injection and clipboard operations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from linux_whispr.events import EventBus
from linux_whispr.output.clipboard import Clipboard
from linux_whispr.output.injector import TextInjector
from linux_whispr.platform.detect import DisplayServer, PlatformInfo


def _make_x11_platform(**overrides: bool) -> PlatformInfo:
    """Create a mock X11 PlatformInfo."""
    defaults = dict(
        display_server=DisplayServer.X11,
        desktop=MagicMock(),
        has_xdotool=True,
        has_wtype=False,
        has_ydotool=False,
        has_xclip=True,
        has_xsel=False,
        has_wl_clipboard=False,
    )
    defaults.update(overrides)
    return PlatformInfo(**defaults)


def _make_wayland_platform(**overrides: bool) -> PlatformInfo:
    """Create a mock Wayland PlatformInfo."""
    defaults = dict(
        display_server=DisplayServer.WAYLAND,
        desktop=MagicMock(),
        has_xdotool=False,
        has_wtype=True,
        has_ydotool=False,
        has_xclip=False,
        has_xsel=False,
        has_wl_clipboard=True,
    )
    defaults.update(overrides)
    return PlatformInfo(**defaults)


class TestPlatformInfo:
    def test_x11_best_injection_tool(self) -> None:
        platform = _make_x11_platform()
        assert platform.best_injection_tool == "xdotool"

    def test_wayland_best_injection_tool(self) -> None:
        platform = _make_wayland_platform()
        assert platform.best_injection_tool == "wtype"

    def test_wayland_fallback_to_ydotool(self) -> None:
        platform = _make_wayland_platform(has_wtype=False, has_ydotool=True)
        assert platform.best_injection_tool == "ydotool"

    def test_x11_best_clipboard_tool(self) -> None:
        platform = _make_x11_platform()
        assert platform.best_clipboard_tool == "xclip"

    def test_wayland_best_clipboard_tool(self) -> None:
        platform = _make_wayland_platform()
        assert platform.best_clipboard_tool == "wl-clipboard"

    def test_no_tools_returns_none(self) -> None:
        platform = PlatformInfo(
            display_server=DisplayServer.X11,
            desktop=MagicMock(),
            has_xdotool=False,
            has_wtype=False,
            has_ydotool=False,
            has_xclip=False,
            has_xsel=False,
            has_wl_clipboard=False,
        )
        assert platform.best_injection_tool is None
        assert platform.best_clipboard_tool is None


class TestTextInjector:
    def test_empty_text_returns_false(self) -> None:
        bus = EventBus()
        platform = _make_x11_platform()
        injector = TextInjector(event_bus=bus, platform=platform)
        assert not injector.inject("")

    @patch("linux_whispr.output.clipboard.time.sleep")
    @patch("linux_whispr.output.clipboard.subprocess.Popen")
    @patch("linux_whispr.output.injector.subprocess.run")
    def test_inject_emits_complete_event(
        self, mock_inject_run: MagicMock, mock_popen: MagicMock, mock_sleep: MagicMock
    ) -> None:
        bus = EventBus()
        events: list[str] = []
        bus.on("inject.complete", lambda **kw: events.append("complete"))

        # Mock xclip Popen clipboard write success
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc
        # Mock paste simulation success
        mock_inject_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        platform = _make_x11_platform()
        injector = TextInjector(
            event_bus=bus,
            platform=platform,
            preserve_clipboard=False,
        )
        result = injector.inject("hello world")

        assert result is True
        assert "complete" in events

    def test_no_injection_tool_still_copies_to_clipboard(self) -> None:
        bus = EventBus()
        events: list[str] = []
        bus.on("inject.error", lambda **kw: events.append("error"))

        platform = PlatformInfo(
            display_server=DisplayServer.X11,
            desktop=MagicMock(),
            has_xdotool=False,
            has_wtype=False,
            has_ydotool=False,
            has_xclip=True,
            has_xsel=False,
            has_wl_clipboard=False,
        )

        with patch("linux_whispr.output.clipboard.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            injector = TextInjector(event_bus=bus, platform=platform, preserve_clipboard=False)
            result = injector.inject("hello")

        # Should fail on paste but text is in clipboard
        assert result is False
        assert "error" in events
