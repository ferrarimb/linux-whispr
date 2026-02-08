"""Wayland global hotkey listener using D-Bus GlobalShortcuts portal."""

from __future__ import annotations

import logging
import threading
from typing import Callable

from linux_whispr.input.hotkey import HotkeyListener

logger = logging.getLogger(__name__)

# XDG Desktop Portal GlobalShortcuts interface
PORTAL_BUS = "org.freedesktop.portal.Desktop"
PORTAL_PATH = "/org/freedesktop/portal/desktop"
PORTAL_IFACE = "org.freedesktop.portal.GlobalShortcuts"


class WaylandHotkeyListener(HotkeyListener):
    """Global hotkey listener using the XDG Desktop Portal GlobalShortcuts.

    This works on GNOME 45+, KDE Plasma 5.27+, and other portal-supporting compositors.
    """

    def __init__(self) -> None:
        self._bindings: list[tuple[str, Callable[[], None], str]] = []
        self._thread: threading.Thread | None = None
        self._running = False
        self._session_handle: str | None = None

    def register(self, hotkey: str, callback: Callable[[], None], name: str = "") -> None:
        self._bindings.append((hotkey, callback, name or hotkey))
        logger.info("Registered Wayland hotkey: %s (%s)", hotkey, name)

    def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="wayland-hotkey"
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._close_session()

    def _listen_loop(self) -> None:
        """Main D-Bus event loop for GlobalShortcuts portal."""
        try:
            import dbus
            from dbus.mainloop.glib import DBusGMainLoop
            from gi.repository import GLib
        except ImportError:
            logger.error(
                "D-Bus/GLib bindings not available. "
                "Install dbus-python and PyGObject for Wayland hotkey support."
            )
            return

        DBusGMainLoop(set_as_default=True)
        bus = dbus.SessionBus()

        try:
            portal = bus.get_object(PORTAL_BUS, PORTAL_PATH)
            shortcuts_iface = dbus.Interface(portal, PORTAL_IFACE)
        except dbus.DBusException:
            logger.error(
                "GlobalShortcuts portal not available. "
                "Your compositor may not support xdg-desktop-portal GlobalShortcuts."
            )
            return

        # Create a session
        try:
            options = dbus.Dictionary(
                {
                    "handle_token": dbus.String("linux_whispr_session"),
                    "session_handle_token": dbus.String("linux_whispr"),
                },
                signature="sv",
            )
            result = shortcuts_iface.CreateSession(options)
            logger.info("GlobalShortcuts session created: %s", result)
        except dbus.DBusException:
            logger.exception("Failed to create GlobalShortcuts session")
            return

        # Build shortcuts list
        shortcuts = dbus.Array([], signature="(sa{sv})")
        callback_map: dict[str, Callable[[], None]] = {}

        for i, (hotkey, callback, name) in enumerate(self._bindings):
            shortcut_id = f"linux-whispr-{i}"
            shortcut = dbus.Struct(
                (
                    dbus.String(shortcut_id),
                    dbus.Dictionary(
                        {
                            "description": dbus.String(name),
                            "preferred_trigger": dbus.String(hotkey),
                        },
                        signature="sv",
                    ),
                ),
                signature="sa{sv}",
            )
            shortcuts.append(shortcut)
            callback_map[shortcut_id] = callback

        # Bind shortcuts
        try:
            bind_options = dbus.Dictionary(
                {"handle_token": dbus.String("linux_whispr_bind")},
                signature="sv",
            )
            shortcuts_iface.BindShortcuts(
                dbus.ObjectPath(result) if isinstance(result, str) else result,
                shortcuts,
                "",  # parent_window
                bind_options,
            )
            logger.info("GlobalShortcuts bound: %d shortcut(s)", len(shortcuts))
        except dbus.DBusException:
            logger.exception("Failed to bind shortcuts")
            return

        # Listen for Activated signal
        def on_activated(
            session_handle: str, shortcut_id: str, timestamp: int, options: dict
        ) -> None:
            cb = callback_map.get(shortcut_id)
            if cb:
                try:
                    cb()
                except Exception:
                    logger.exception("Error in hotkey callback for %s", shortcut_id)

        bus.add_signal_receiver(
            on_activated,
            signal_name="Activated",
            dbus_interface=PORTAL_IFACE,
        )

        logger.info("Wayland hotkey listener running")

        # Run GLib main loop
        loop = GLib.MainLoop()
        while self._running:
            context = loop.get_context()
            context.iteration(True)

        logger.info("Wayland hotkey listener stopped")

    def _close_session(self) -> None:
        """Close the D-Bus session."""
        # Session is cleaned up when the D-Bus connection closes
        pass
