"""Desktop notifications via D-Bus."""

from __future__ import annotations

import logging
import subprocess

from linux_whispr.constants import APP_NAME

logger = logging.getLogger(__name__)


def notify(
    title: str,
    body: str = "",
    urgency: str = "normal",
    timeout_ms: int = 5000,
) -> None:
    """Send a desktop notification using notify-send.

    Args:
        title: Notification title.
        body: Notification body text.
        urgency: "low", "normal", or "critical".
        timeout_ms: Time in milliseconds before auto-dismiss.
    """
    try:
        cmd = [
            "notify-send",
            "--app-name", APP_NAME,
            "--urgency", urgency,
            "--expire-time", str(timeout_ms),
            title,
        ]
        if body:
            cmd.append(body)

        subprocess.run(cmd, capture_output=True, timeout=5)
    except FileNotFoundError:
        logger.debug("notify-send not found, skipping notification")
    except Exception:
        logger.debug("Failed to send notification", exc_info=True)
