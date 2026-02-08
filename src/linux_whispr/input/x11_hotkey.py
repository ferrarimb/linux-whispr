"""X11 global hotkey listener using python-xlib XGrabKey."""

from __future__ import annotations

import logging
import threading
from typing import Callable

from linux_whispr.input.hotkey import HotkeyListener

logger = logging.getLogger(__name__)

# Modifier masks for XGrabKey
_MODIFIER_MAP = {
    "ctrl": "ControlMask",
    "control": "ControlMask",
    "shift": "ShiftMask",
    "alt": "Mod1Mask",
    "super": "Mod4Mask",
    "meta": "Mod4Mask",
    "hyper": "Mod4Mask",
}


def _parse_hotkey(hotkey_str: str) -> tuple[list[str], str]:
    """Parse a hotkey string like '<Ctrl><Shift>h' or 'F12' into modifiers + key.

    Returns:
        Tuple of (modifier_names, key_name).
    """
    import re

    modifiers: list[str] = []
    remaining = hotkey_str

    # Extract <Modifier> patterns
    for match in re.finditer(r"<(\w+)>", hotkey_str):
        mod = match.group(1).lower()
        if mod in _MODIFIER_MAP:
            modifiers.append(mod)
        remaining = remaining.replace(match.group(0), "")

    key = remaining.strip()
    if not key:
        raise ValueError(f"No key found in hotkey string: {hotkey_str!r}")

    return modifiers, key


class X11HotkeyListener(HotkeyListener):
    """Global hotkey listener using X11 XGrabKey via python-xlib."""

    def __init__(self) -> None:
        self._bindings: list[tuple[str, Callable[[], None], str]] = []
        self._thread: threading.Thread | None = None
        self._running = False

    def register(self, hotkey: str, callback: Callable[[], None], name: str = "") -> None:
        self._bindings.append((hotkey, callback, name))
        logger.info("Registered X11 hotkey: %s (%s)", hotkey, name)

    def start(self) -> None:
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True, name="x11-hotkey")
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _listen_loop(self) -> None:
        """Main X11 event loop for hotkey listening."""
        try:
            from Xlib import X, XK, display
            from Xlib.ext import record
            from Xlib.protocol import rq
        except ImportError:
            logger.error("python-xlib not installed. Install with: pip install python-xlib")
            return

        disp = display.Display()
        root = disp.screen().root

        # Build keycode/modifier mappings for our bindings
        grab_specs: list[tuple[int, int, Callable[[], None]]] = []
        for hotkey_str, callback, name in self._bindings:
            modifiers, key_name = _parse_hotkey(hotkey_str)

            # Get keycode
            keysym = XK.string_to_keysym(key_name)
            if keysym == 0:
                # Try common aliases
                keysym = XK.string_to_keysym(key_name.capitalize())
            if keysym == 0:
                logger.error("Unknown key: %s", key_name)
                continue

            keycode = disp.keysym_to_keycode(keysym)
            if keycode == 0:
                logger.error("Cannot map key '%s' to keycode", key_name)
                continue

            # Build modifier mask
            mod_mask = 0
            for mod in modifiers:
                xlib_mod = _MODIFIER_MAP.get(mod)
                if xlib_mod == "ControlMask":
                    mod_mask |= X.ControlMask
                elif xlib_mod == "ShiftMask":
                    mod_mask |= X.ShiftMask
                elif xlib_mod == "Mod1Mask":
                    mod_mask |= X.Mod1Mask
                elif xlib_mod == "Mod4Mask":
                    mod_mask |= X.Mod4Mask

            # Grab the key on root window
            # We grab with and without NumLock (Mod2Mask) and CapsLock (LockMask)
            for extra_mod in [0, X.Mod2Mask, X.LockMask, X.Mod2Mask | X.LockMask]:
                root.grab_key(
                    keycode,
                    mod_mask | extra_mod,
                    True,
                    X.GrabModeAsync,
                    X.GrabModeAsync,
                )

            grab_specs.append((keycode, mod_mask, callback))
            logger.info("X11: grabbed keycode=%d, mod_mask=%d for '%s'", keycode, mod_mask, name)

        if not grab_specs:
            logger.error("No hotkeys could be registered")
            return

        logger.info("X11 hotkey listener running")

        while self._running:
            # Process pending events with a timeout
            while disp.pending_events() > 0 and self._running:
                event = disp.next_event()
                if event.type == X.KeyPress:
                    for keycode, mod_mask, callback in grab_specs:
                        # Mask out NumLock and CapsLock for comparison
                        clean_state = event.state & ~(X.Mod2Mask | X.LockMask)
                        if event.detail == keycode and clean_state == mod_mask:
                            try:
                                callback()
                            except Exception:
                                logger.exception("Error in hotkey callback")

            # Small sleep to avoid busy-waiting
            import time

            time.sleep(0.05)

        # Ungrab keys
        for keycode, mod_mask, _ in grab_specs:
            for extra_mod in [0, X.Mod2Mask, X.LockMask, X.Mod2Mask | X.LockMask]:
                root.ungrab_key(keycode, mod_mask | extra_mod)

        disp.close()
        logger.info("X11 hotkey listener stopped")
