"""Fallback hotkey listener using pynput (works on X11 and some Wayland setups)."""

from __future__ import annotations

import logging
import threading
from typing import Callable

from linux_whispr.input.hotkey import HotkeyListener

logger = logging.getLogger(__name__)


def _parse_hotkey_to_pynput(hotkey_str: str) -> set[object]:
    """Parse a hotkey string into pynput key objects."""
    import re

    from pynput.keyboard import Key, KeyCode

    keys: set[object] = set()
    remaining = hotkey_str

    # Extract <Modifier> patterns
    modifier_map = {
        "ctrl": Key.ctrl_l,
        "control": Key.ctrl_l,
        "shift": Key.shift_l,
        "alt": Key.alt_l,
        "super": Key.cmd,
        "meta": Key.cmd,
    }

    for match in re.finditer(r"<(\w+)>", hotkey_str):
        mod = match.group(1).lower()
        if mod in modifier_map:
            keys.add(modifier_map[mod])
        remaining = remaining.replace(match.group(0), "")

    key_name = remaining.strip().lower()
    if key_name:
        # Try as a special key first (F1-F12, etc.)
        try:
            keys.add(getattr(Key, key_name.lower()))
        except AttributeError:
            # Regular character key
            if len(key_name) == 1:
                keys.add(KeyCode.from_char(key_name))
            else:
                logger.error("Unknown key: %s", key_name)

    return keys


class PynputHotkeyListener(HotkeyListener):
    """Fallback hotkey listener using pynput."""

    def __init__(self) -> None:
        self._bindings: list[tuple[set[object], Callable[[], None]]] = []
        self._listener: object | None = None
        self._current_keys: set[object] = set()

    def register(self, hotkey: str, callback: Callable[[], None], name: str = "") -> None:
        keys = _parse_hotkey_to_pynput(hotkey)
        if keys:
            self._bindings.append((keys, callback))
            logger.info("Registered pynput hotkey: %s (%s) -> %s", hotkey, name, keys)

    def start(self) -> None:
        from pynput.keyboard import Listener

        self._listener = Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.start()  # type: ignore[union-attr]
        logger.info("pynput hotkey listener running")

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()  # type: ignore[union-attr]
            logger.info("pynput hotkey listener stopped")

    def _on_press(self, key: object) -> None:
        self._current_keys.add(key)
        for combo, callback in self._bindings:
            if combo.issubset(self._current_keys):
                try:
                    callback()
                except Exception:
                    logger.exception("Error in hotkey callback")

    def _on_release(self, key: object) -> None:
        self._current_keys.discard(key)
