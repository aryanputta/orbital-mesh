import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine
from collections import defaultdict


class EventTopic(str, Enum):
    TELEMETRY_RECEIVED = "telemetry.received"
    ANOMALY_DETECTED = "anomaly.detected"
    NODE_FAILED = "node.failed"
    NODE_RECOVERED = "node.recovered"
    FAILOVER_TRIGGERED = "failover.triggered"
    REROUTE_COMPLETE = "reroute.complete"
    PROTOCOL_SWITCHED = "protocol.switched"
    HEARTBEAT = "node.heartbeat"
    CONTROL_COMMAND = "control.command"


@dataclass
class Event:
    topic: EventTopic
    payload: dict[str, Any]
    source_node: str | None = None


Handler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[EventTopic, list[asyncio.Queue]] = defaultdict(list)
        self._wildcard_subscribers: list[asyncio.Queue] = []

    def subscribe(self, topic: EventTopic) -> asyncio.Queue:
        q: asyncio.Queue[Event] = asyncio.Queue(maxsize=1000)
        self._subscribers[topic].append(q)
        return q

    def subscribe_all(self) -> asyncio.Queue:
        q: asyncio.Queue[Event] = asyncio.Queue(maxsize=5000)
        self._wildcard_subscribers.append(q)
        return q

    def unsubscribe(self, topic: EventTopic, queue: asyncio.Queue) -> None:
        if queue in self._subscribers[topic]:
            self._subscribers[topic].remove(queue)

    def unsubscribe_all(self, queue: asyncio.Queue) -> None:
        if queue in self._wildcard_subscribers:
            self._wildcard_subscribers.remove(queue)

    async def publish(self, topic: EventTopic, payload: dict[str, Any], source_node: str | None = None) -> None:
        event = Event(topic=topic, payload=payload, source_node=source_node)
        for q in list(self._subscribers[topic]):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass
        for q in list(self._wildcard_subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


def reset_event_bus() -> None:
    global _bus
    _bus = None
