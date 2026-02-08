"""Entry point: python -m linux_whispr"""

from __future__ import annotations

import argparse
import logging
import signal
import sys

from linux_whispr import __version__
from linux_whispr.constants import CONFIG_DIR, DATA_DIR, LOG_FORMAT, MODELS_DIR


def setup_logging(verbose: bool = False) -> None:
    """Configure logging with rich handler if available."""
    level = logging.DEBUG if verbose else logging.INFO

    try:
        from rich.logging import RichHandler

        logging.basicConfig(
            level=level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True)],
        )
    except ImportError:
        logging.basicConfig(level=level, format=LOG_FORMAT)


def ensure_directories() -> None:
    """Create application directories if they don't exist."""
    for d in [CONFIG_DIR, DATA_DIR, MODELS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="linux-whispr",
        description="Privacy-first voice dictation for Linux",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )
    parser.add_argument(
        "--version", action="version", version=f"linux-whispr {__version__}"
    )
    parser.add_argument(
        "--config", type=str, default=None, help="Path to config file"
    )
    parser.add_argument(
        "--no-tray", action="store_true", help="Run without system tray icon"
    )
    parser.add_argument(
        "--setup", action="store_true", help="Re-run the first-time setup wizard"
    )
    parser.add_argument(
        "--list-devices", action="store_true", help="List audio input devices and exit"
    )
    parser.add_argument(
        "--list-models", action="store_true", help="List available Whisper models and exit"
    )
    return parser.parse_args()


def cmd_list_devices() -> None:
    """Print available audio input devices and exit."""
    try:
        from linux_whispr.audio.devices import list_input_devices

        devices = list_input_devices()
        if not devices:
            print("No audio input devices found.")
            return
        for dev in devices:
            marker = " *" if dev.is_default else ""
            print(f"  [{dev.index}] {dev.name} ({dev.channels}ch){marker}")
    except OSError as e:
        print(f"Error: {e}")


def cmd_list_models() -> None:
    """Print available Whisper models and their download status."""
    from linux_whispr.stt.model_manager import ModelManager

    mm = ModelManager()
    for m in mm.list_models():
        status = "✓ downloaded" if m.downloaded else "  not downloaded"
        print(f"  {m.name:<20} ~{m.size_mb:>5}MB  {status}")


def main() -> None:
    """Main entry point."""
    args = parse_args()
    setup_logging(verbose=args.verbose)
    ensure_directories()

    logger = logging.getLogger("linux_whispr")

    # Handle info commands that exit immediately
    if args.list_devices:
        cmd_list_devices()
        return

    if args.list_models:
        cmd_list_models()
        return

    logger.info("LinuxWhispr v%s starting...", __version__)

    from pathlib import Path

    from linux_whispr.config import AppConfig

    # Load config
    config_path = Path(args.config) if args.config else None
    config = AppConfig.load(config_path)

    # First-run wizard
    if config.first_run or args.setup:
        logger.info("Running setup wizard...")
        from linux_whispr.events import event_bus
        from linux_whispr.ui.wizard import SetupWizard

        wizard = SetupWizard(config=config, event_bus=event_bus)
        wizard.run()
        # Config is saved by the wizard; reload in case wizard modified it
        config = AppConfig.load(config_path)

    # Create and setup application
    from linux_whispr.app import LinuxWhispr

    app = LinuxWhispr(config=config)

    try:
        app.setup()
        app.start()

        logger.info("LinuxWhispr is running. Press Ctrl+C to stop.")
        _run_main_loop(logger)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception:
        logger.exception("Fatal error")
        sys.exit(1)
    finally:
        app.stop()


def _run_main_loop(logger: logging.Logger) -> None:
    """Run the GLib main loop so GTK overlay events are processed.

    Falls back to signal.pause() when GLib is not available (overlay
    will be disabled but core dictation still works).
    """
    try:
        from gi.repository import GLib

        loop = GLib.MainLoop()

        def _on_shutdown(*_args: object) -> bool:
            loop.quit()
            return GLib.SOURCE_REMOVE

        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, _on_shutdown)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, _on_shutdown)

        loop.run()
    except ImportError:
        logger.debug("GLib not available, falling back to signal.pause()")

        def _signal_handler(sig: int, frame: object) -> None:
            sys.exit(0)

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)
        signal.pause()


if __name__ == "__main__":
    main()
