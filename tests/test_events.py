"""Tests for the event bus."""

from __future__ import annotations

from linux_whispr.events import EventBus


class TestEventBus:
    def test_emit_calls_handler(self) -> None:
        bus = EventBus()
        received: list[dict] = []

        def handler(**kwargs: object) -> None:
            received.append(dict(kwargs))

        bus.on("test.event", handler)
        bus.emit("test.event", foo="bar", num=42)

        assert len(received) == 1
        assert received[0] == {"foo": "bar", "num": 42}

    def test_multiple_handlers(self) -> None:
        bus = EventBus()
        calls: list[str] = []

        bus.on("test", lambda **kw: calls.append("a"))
        bus.on("test", lambda **kw: calls.append("b"))
        bus.emit("test")

        assert calls == ["a", "b"]

    def test_off_removes_handler(self) -> None:
        bus = EventBus()
        calls: list[str] = []

        def handler(**kw: object) -> None:
            calls.append("called")

        bus.on("test", handler)
        bus.off("test", handler)
        bus.emit("test")

        assert calls == []

    def test_no_handlers_no_error(self) -> None:
        bus = EventBus()
        bus.emit("nonexistent.event")  # Should not raise

    def test_handler_error_doesnt_crash(self) -> None:
        bus = EventBus()
        calls: list[str] = []

        def bad_handler(**kw: object) -> None:
            raise ValueError("boom")

        def good_handler(**kw: object) -> None:
            calls.append("ok")

        bus.on("test", bad_handler)
        bus.on("test", good_handler)
        bus.emit("test")

        assert calls == ["ok"]

    def test_clear(self) -> None:
        bus = EventBus()
        calls: list[str] = []

        bus.on("test", lambda **kw: calls.append("x"))
        bus.clear()
        bus.emit("test")

        assert calls == []
