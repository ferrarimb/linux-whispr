"""Floating overlay widget (GTK4) — minimal pill indicator at bottom-center."""

from __future__ import annotations

import logging
import math
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from linux_whispr.events import EventBus

logger = logging.getLogger(__name__)


class OverlayState(Enum):
    """Visual states of the overlay widget."""

    HIDDEN = auto()
    IDLE = auto()
    RECORDING = auto()
    PROCESSING = auto()
    DONE = auto()
    ERROR = auto()
    COMMAND = auto()


# --- Design tokens --------------------------------------------------------- #
_PILL_HEIGHT = 30
_PILL_PADDING_H = 14
_DOT_RADIUS = 4.5
_CORNER_RADIUS = 15
_BG_COLOR = (0.08, 0.08, 0.10, 0.82)  # dark semi-transparent
_FONT_SIZE = 11.0
_BOTTOM_MARGIN = 48  # px from screen bottom edge

_STATE_COLORS: dict[OverlayState, tuple[float, float, float]] = {
    OverlayState.RECORDING: (0.93, 0.26, 0.26),   # soft red
    OverlayState.PROCESSING: (0.40, 0.58, 0.96),   # soft blue
    OverlayState.DONE: (0.30, 0.78, 0.47),         # soft green
    OverlayState.ERROR: (0.95, 0.55, 0.20),        # orange
    OverlayState.COMMAND: (0.55, 0.40, 0.95),      # purple
}

_STATE_LABELS: dict[OverlayState, str] = {
    OverlayState.RECORDING: "Recording",
    OverlayState.PROCESSING: "Processing\u2026",   # ellipsis
    OverlayState.DONE: "Done",
    OverlayState.ERROR: "Error",
    OverlayState.COMMAND: "Listening\u2026",
}


class Overlay:
    """Floating pill-shaped overlay at the bottom-center of the screen.

    Shows recording / processing / done state with a colored dot and label.
    On Wayland: uses gtk4-layer-shell for always-on-top, non-focusable surface.
    On X11: uses regular window with best-effort positioning.

    Falls back to a no-op if GTK4 is not available.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._state = OverlayState.HIDDEN
        self._window: object | None = None
        self._gtk_available = False
        self._audio_level: float = 0.0
        self._anim_tick: int = 0
        self._anim_source_id: int | None = None
        self._layer_shell = False
        self._pill_width: int = 0
        self._x11_hints_applied = False

        self._try_init_gtk()

    def _try_init_gtk(self) -> None:
        """Try to initialize GTK4. Gracefully degrade if unavailable."""
        try:
            import gi

            gi.require_version("Gtk", "4.0")
            gi.require_version("Adw", "1")
            from gi.repository import Adw, Gdk, Gtk

            self._gtk_available = True
            logger.info("GTK4 available for overlay")
        except (ImportError, ValueError):
            logger.warning(
                "GTK4/libadwaita not available. Overlay will be disabled. "
                "Install PyGObject, GTK4, and libadwaita for overlay support."
            )

    def setup(self) -> None:
        """Create the overlay window and register event handlers."""
        if not self._gtk_available:
            self._register_events_noop()
            return

        self._create_window()
        self._register_events()
        logger.info("Overlay initialized")

    def _create_window(self) -> None:
        """Create the GTK4 overlay window."""
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gdk, Gtk

        # Compute pill width to fit the longest label
        longest = max(_STATE_LABELS.values(), key=len)
        char_w = _FONT_SIZE * 0.62
        self._pill_width = int(
            _PILL_PADDING_H * 2 + _DOT_RADIUS * 2 + 8 + len(longest) * char_w + 4
        )

        # Create a small frameless window
        self._window = Gtk.Window()
        self._window.set_title("LinuxWhispr Overlay")
        self._window.set_default_size(self._pill_width, _PILL_HEIGHT)
        self._window.set_resizable(False)
        self._window.set_decorated(False)
        self._window.set_deletable(False)
        self._window.set_can_focus(False)
        self._window.set_focusable(False)

        # Try layer shell for Wayland
        try:
            gi.require_version("Gtk4LayerShell", "1.0")
            from gi.repository import Gtk4LayerShell

            Gtk4LayerShell.init_for_window(self._window)
            Gtk4LayerShell.set_layer(self._window, Gtk4LayerShell.Layer.OVERLAY)
            Gtk4LayerShell.set_keyboard_mode(
                self._window, Gtk4LayerShell.KeyboardMode.NONE
            )
            # Anchor to bottom only → horizontally centered by the compositor
            Gtk4LayerShell.set_anchor(
                self._window, Gtk4LayerShell.Edge.BOTTOM, True
            )
            Gtk4LayerShell.set_margin(
                self._window, Gtk4LayerShell.Edge.BOTTOM, _BOTTOM_MARGIN
            )
            self._layer_shell = True
            logger.info("Using gtk4-layer-shell for Wayland overlay")
        except (ImportError, ValueError):
            logger.debug("gtk4-layer-shell not available, using regular window")

        # Build the overlay content
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the overlay UI components."""
        if self._window is None:
            return

        from gi.repository import Gdk, Gtk

        # Single drawing area for the pill
        self._drawing_area = Gtk.DrawingArea()
        self._drawing_area.set_content_width(self._pill_width)
        self._drawing_area.set_content_height(_PILL_HEIGHT)
        self._drawing_area.set_draw_func(self._draw_pill)
        self._window.set_child(self._drawing_area)

        # Apply CSS for transparent window background
        css = b"""
        window, window * {
            background-color: transparent;
            background: none;
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    # --- Drawing ----------------------------------------------------------- #

    def _draw_pill(
        self, area: object, cr: object, width: int, height: int
    ) -> None:
        """Draw the pill-shaped indicator with dot + label."""
        if self._state in (OverlayState.HIDDEN, OverlayState.IDLE):
            return

        dot_color = _STATE_COLORS.get(self._state, (0.5, 0.5, 0.5))
        label = _STATE_LABELS.get(self._state, "")
        r, g, b = dot_color

        # --- Pill background (rounded rectangle) ---
        self._draw_rounded_rect(cr, 0, 0, width, height, _CORNER_RADIUS)
        cr.set_source_rgba(*_BG_COLOR)
        cr.fill()

        dot_cx = _PILL_PADDING_H + _DOT_RADIUS
        dot_cy = height / 2.0

        # --- State-specific dot / icon ---
        if self._state == OverlayState.RECORDING:
            # Pulsing glow halo
            pulse = 0.5 + 0.5 * math.sin(self._anim_tick * 0.15)
            glow_r = _DOT_RADIUS + 3.0 * pulse
            cr.arc(dot_cx, dot_cy, glow_r, 0, 2 * math.pi)
            cr.set_source_rgba(r, g, b, 0.22 * pulse)
            cr.fill()
            # Solid dot
            cr.arc(dot_cx, dot_cy, _DOT_RADIUS, 0, 2 * math.pi)
            cr.set_source_rgba(r, g, b, 1.0)
            cr.fill()

        elif self._state == OverlayState.PROCESSING:
            # Three orbiting dots (spinner)
            angle_base = self._anim_tick * 0.10
            for i in range(3):
                a = angle_base + i * (2 * math.pi / 3)
                ox = math.cos(a) * (_DOT_RADIUS * 0.85)
                oy = math.sin(a) * (_DOT_RADIUS * 0.85)
                alpha = 0.30 + 0.70 * ((i + 1) / 3)
                cr.arc(dot_cx + ox, dot_cy + oy, 2.0, 0, 2 * math.pi)
                cr.set_source_rgba(r, g, b, alpha)
                cr.fill()

        elif self._state == OverlayState.DONE:
            # Small checkmark icon
            cr.set_line_width(2.0)
            cr.set_line_cap(1)   # CAIRO_LINE_CAP_ROUND
            cr.set_line_join(1)  # CAIRO_LINE_JOIN_ROUND
            cr.move_to(dot_cx - 4, dot_cy)
            cr.line_to(dot_cx - 1, dot_cy + 3)
            cr.line_to(dot_cx + 4, dot_cy - 3)
            cr.set_source_rgba(r, g, b, 1.0)
            cr.stroke()

        else:
            # Regular solid dot (ERROR, COMMAND, etc.)
            cr.arc(dot_cx, dot_cy, _DOT_RADIUS, 0, 2 * math.pi)
            cr.set_source_rgba(r, g, b, 1.0)
            cr.fill()

        # --- Label text ---
        text_x = dot_cx + _DOT_RADIUS + 8
        cr.select_font_face("sans-serif", 0, 0)  # normal slant, normal weight
        cr.set_font_size(_FONT_SIZE)
        cr.set_source_rgba(0.92, 0.92, 0.94, 0.92)
        extents = cr.text_extents(label)
        text_y = height / 2.0 + extents.height / 2.0
        cr.move_to(text_x, text_y)
        cr.show_text(label)

    @staticmethod
    def _draw_rounded_rect(
        cr: object, x: float, y: float, w: float, h: float, r: float
    ) -> None:
        """Draw a rounded-rectangle path (does not fill or stroke)."""
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()

    # --- Animation --------------------------------------------------------- #

    def _start_animation(self) -> None:
        """Start the ~30 fps animation tick for pulse / spinner effects."""
        if self._anim_source_id is not None or not self._gtk_available:
            return

        from gi.repository import GLib

        self._anim_tick = 0
        self._anim_source_id = GLib.timeout_add(33, self._on_anim_tick)

    def _stop_animation(self) -> None:
        """Stop the animation tick."""
        if self._anim_source_id is not None:
            from gi.repository import GLib

            GLib.source_remove(self._anim_source_id)
            self._anim_source_id = None

    def _on_anim_tick(self) -> bool:
        """Animation frame callback (GLib timeout)."""
        self._anim_tick += 1
        if hasattr(self, "_drawing_area"):
            self._drawing_area.queue_draw()
        # Keep running while in an animated state
        if self._state in (OverlayState.RECORDING, OverlayState.PROCESSING):
            return True
        # Stop the timer
        self._anim_source_id = None
        return False

    # --- Event bus handlers ------------------------------------------------ #

    def _register_events(self) -> None:
        """Register event bus handlers for state updates."""
        self._event_bus.on("hotkey.dictation.start", self._on_recording_start)
        self._event_bus.on("hotkey.dictation.stop", self._on_recording_stop)
        self._event_bus.on("hotkey.command.start", self._on_command_start)
        self._event_bus.on("stt.started", self._on_processing)
        self._event_bus.on("inject.complete", self._on_done)
        self._event_bus.on("inject.error", self._on_error)
        self._event_bus.on("audio.level", self._on_audio_level)

    def _register_events_noop(self) -> None:
        """Register logging-only event handlers when GTK is unavailable."""
        self._event_bus.on(
            "hotkey.dictation.start",
            lambda **kw: logger.info("[Overlay] Recording started"),
        )
        self._event_bus.on(
            "stt.started",
            lambda **kw: logger.info("[Overlay] Processing..."),
        )
        self._event_bus.on(
            "inject.complete",
            lambda **kw: logger.info("[Overlay] Done ✓"),
        )
        self._event_bus.on(
            "inject.error",
            lambda **kw: logger.info("[Overlay] Error: %s", kw.get("error", "")),
        )

    def _set_state(self, state: OverlayState) -> None:
        """Update visual state and redraw."""
        self._state = state
        if self._gtk_available and hasattr(self, "_drawing_area"):
            from gi.repository import GLib

            GLib.idle_add(self._drawing_area.queue_draw)

    def _on_recording_start(self, **kwargs: object) -> None:
        self._set_state(OverlayState.RECORDING)
        self.show()
        self._start_animation()

    def _on_recording_stop(self, **kwargs: object) -> None:
        pass  # Will transition to PROCESSING via stt.started

    def _on_command_start(self, **kwargs: object) -> None:
        self._set_state(OverlayState.COMMAND)
        self.show()

    def _on_processing(self, **kwargs: object) -> None:
        self._set_state(OverlayState.PROCESSING)
        self._start_animation()

    def _on_done(self, **kwargs: object) -> None:
        self._stop_animation()
        self._set_state(OverlayState.DONE)
        if self._gtk_available:
            from gi.repository import GLib

            GLib.timeout_add(1200, self._return_to_idle)
        else:
            self._return_to_idle()

    def _on_error(self, **kwargs: object) -> None:
        self._stop_animation()
        self._set_state(OverlayState.ERROR)
        if self._gtk_available:
            from gi.repository import GLib

            GLib.timeout_add(3000, self._return_to_idle)

    def _on_audio_level(self, level: float = 0.0, **kwargs: object) -> None:
        self._audio_level = level

    def _return_to_idle(self) -> bool:
        self._set_state(OverlayState.HIDDEN)
        self.hide()
        return False  # Don't repeat GLib timeout

    # --- X11 overlay hints ------------------------------------------------- #

    def _apply_x11_overlay_hints(self) -> bool:
        """Make the overlay always-on-top and position it at bottom-center on X11.

        Uses python-xlib to send _NET_WM_STATE client messages and set
        _NET_WM_WINDOW_TYPE to NOTIFICATION.  No-op when layer-shell is active.
        """
        if self._layer_shell or self._window is None:
            return False

        try:
            import gi

            gi.require_version("GdkX11", "4.0")
            from gi.repository import GdkX11

            surface = self._window.get_surface()
            if surface is None or not isinstance(surface, GdkX11.X11Surface):
                return False

            xid = surface.get_xid()

            from Xlib import X, Xatom
            from Xlib import display as xdisplay
            from Xlib.protocol import event as xevent

            d = xdisplay.Display()
            root = d.screen().root
            w = d.create_resource_object("window", xid)

            # --- Window type: NOTIFICATION (skip taskbar, no focus) ---
            wm_type = d.intern_atom("_NET_WM_WINDOW_TYPE")
            type_notif = d.intern_atom("_NET_WM_WINDOW_TYPE_NOTIFICATION")
            w.change_property(wm_type, Xatom.ATOM, 32, [type_notif])

            # --- Position at bottom-center ---
            screen = d.screen()
            x = (screen.width_in_pixels - self._pill_width) // 2
            y = screen.height_in_pixels - _PILL_HEIGHT - _BOTTOM_MARGIN
            w.configure(x=x, y=y)

            # --- Always-on-top + skip taskbar/pager via _NET_WM_STATE ---
            wm_state = d.intern_atom("_NET_WM_STATE")
            _ADD = 1  # _NET_WM_STATE_ADD
            for name in (
                "_NET_WM_STATE_ABOVE",
                "_NET_WM_STATE_SKIP_TASKBAR",
                "_NET_WM_STATE_SKIP_PAGER",
            ):
                atom = d.intern_atom(name)
                ev = xevent.ClientMessage(
                    window=w,
                    client_type=wm_state,
                    data=(32, [_ADD, atom, 0, 1, 0]),
                )
                root.send_event(
                    ev,
                    event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask,
                )

            d.flush()
            d.close()
            self._x11_hints_applied = True
            logger.debug("X11 overlay hints applied (xid=%d)", xid)
        except Exception:
            logger.debug("Could not apply X11 overlay hints", exc_info=True)

        return False  # Don't repeat GLib timeout

    # --- Show / hide / destroy --------------------------------------------- #

    def show(self) -> None:
        """Show the overlay window."""
        if self._window is not None:
            from gi.repository import GLib

            GLib.idle_add(self._window.present)
            if not self._layer_shell and not self._x11_hints_applied:
                GLib.timeout_add(100, self._apply_x11_overlay_hints)

    def hide(self) -> None:
        """Hide the overlay window."""
        if self._window is not None:
            from gi.repository import GLib

            GLib.idle_add(self._window.hide)

    def destroy(self) -> None:
        """Destroy the overlay window."""
        self._stop_animation()
        if self._window is not None:
            from gi.repository import GLib

            GLib.idle_add(self._window.destroy)
            self._window = None
