"""Internal event bus for inter-component communication."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

# Type alias for event handlers
SyncHandler = Callable[..., None]
AsyncHandler = Callable[..., Coroutine[Any, Any, None]]
Handler = SyncHandler | AsyncHandler


class EventBus:
    """Simple publish/subscribe event bus supporting both sync and async handlers.

    Events are identified by dot-separated string names, e.g.:
        hotkey.dictation.start
        audio.ready
        stt.complete
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the asyncio event loop for scheduling async handlers."""
        self._loop = loop

    def on(self, event: str, handler: Handler) -> None:
        """Subscribe a handler to an event."""
        self._handlers[event].append(handler)
        logger.debug("Registered handler %s for event '%s'", handler.__name__, event)

    def off(self, event: str, handler: Handler) -> None:
        """Unsubscribe a handler from an event."""
        try:
            self._handlers[event].remove(handler)
        except ValueError:
            pass

    def emit(self, event: str, **kwargs: Any) -> None:
        """Emit an event, calling all registered handlers.

        Sync handlers are called directly.
        Async handlers are scheduled on the event loop.
        """
        handlers = self._handlers.get(event, [])
        if not handlers:
            return

        logger.debug("Emitting event '%s' to %d handler(s)", event, len(handlers))
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    if self._loop is not None and self._loop.is_running():
                        self._loop.create_task(handler(**kwargs))
                    else:
                        logger.warning(
                            "Cannot schedule async handler %s: no running event loop",
                            handler.__name__,
                        )
                else:
                    handler(**kwargs)
            except Exception:
                logger.exception(
                    "Error in handler %s for event '%s'", handler.__name__, event
                )

    async def emit_async(self, event: str, **kwargs: Any) -> None:
        """Emit an event asynchronously, awaiting all async handlers."""
        handlers = self._handlers.get(event, [])
        if not handlers:
            return

        logger.debug("Async-emitting event '%s' to %d handler(s)", event, len(handlers))
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(**kwargs)
                else:
                    handler(**kwargs)
            except Exception:
                logger.exception(
                    "Error in handler %s for event '%s'", handler.__name__, event
                )

    def clear(self) -> None:
        """Remove all handlers."""
        self._handlers.clear()


# Global event bus singleton
event_bus = EventBus()
