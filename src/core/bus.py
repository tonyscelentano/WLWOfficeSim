"""
bus.py — Reactive Event Bus

Pub/Sub registry. Multiple subscribers per event, fully isolated exception handling.

Contract:
  - Only engine.py publishes events.
  - Systems (tasks, social, career) and UI subscribe.
  - A failing subscriber never kills sibling subscribers on the same event.
  - Import the module-level `bus` singleton for normal use.
  - Tests: call bus.clear() in teardown.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Callable

log = logging.getLogger(__name__)

Subscriber = Callable[[dict[str, Any]], None]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Subscriber]] = defaultdict(list)

    # ── Registration ─────────────────────────────────────────────────────────

    def subscribe(self, event: str, fn: Subscriber) -> None:
        """Register fn as a listener for event."""
        self._subscribers[event].append(fn)

    def unsubscribe(self, event: str, fn: Subscriber) -> None:
        """Remove fn from event's listener list. Silent no-op if not registered."""
        try:
            self._subscribers[event].remove(fn)
        except ValueError:
            pass

    # ── Publishing ───────────────────────────────────────────────────────────

    def publish(self, event: str, payload: dict[str, Any] | None = None) -> None:
        """
        Dispatch event to all registered subscribers.

        Each subscriber is called in registration order.
        Exceptions are caught per-subscriber: one crash cannot silence others.
        Snapshot the list before iterating to allow safe mid-dispatch unsubscription.
        """
        payload = payload or {}
        listeners = list(self._subscribers[event])  # snapshot
        if not listeners:
            log.debug("Event '%s' fired with no subscribers.", event)
            return
        for fn in listeners:
            try:
                fn(payload)
            except Exception:
                log.exception(
                    "Subscriber '%s' raised on event '%s' — skipped.",
                    getattr(fn, "__qualname__", repr(fn)),
                    event,
                )

    # ── Utility ──────────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Wipe all subscriptions. Use in test teardown."""
        self._subscribers.clear()

    def subscribers(self, event: str) -> list[Subscriber]:
        """Read-only view of subscribers for an event. Useful for debugging."""
        return list(self._subscribers[event])


# ── Singleton ─────────────────────────────────────────────────────────────────
# Import and use directly:
#   from core.bus import bus
#   bus.subscribe("task_resolved", my_handler)
#   bus.publish("task_resolved", {"outcome": "legendary", "rep_delta": 25})
bus = EventBus()
