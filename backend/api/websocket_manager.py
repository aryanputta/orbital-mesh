import asyncio
import datetime
import uuid
from typing import Any

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from core.events import get_event_bus, EventTopic
from core.logging import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._broadcast_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        conn_id = str(uuid.uuid4())
        self._connections[conn_id] = websocket
        logger.info("websocket.connected", conn_id=conn_id, total=len(self._connections))
        return conn_id

    async def disconnect(self, conn_id: str) -> None:
        self._connections.pop(conn_id, None)
        logger.info("websocket.disconnected", conn_id=conn_id, total=len(self._connections))

    async def broadcast(self, topic: str, data: Any) -> None:
        if not self._connections:
            return
        message = {
            "topic": topic,
            "data": data,
            "timestamp": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
        }
        dead: list[str] = []
        tasks = []
        conn_ids = list(self._connections.keys())
        for conn_id in conn_ids:
            ws = self._connections.get(conn_id)
            if ws and ws.client_state == WebSocketState.CONNECTED:
                tasks.append((conn_id, ws.send_json(message)))
            else:
                dead.append(conn_id)

        results = await asyncio.gather(*[t for _, t in tasks], return_exceptions=True)
        for (conn_id, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                dead.append(conn_id)

        for conn_id in dead:
            await self.disconnect(conn_id)

    async def start_broadcast_loop(self) -> None:
        self._broadcast_task = asyncio.create_task(
            self._consume_and_broadcast(), name="websocket.broadcast"
        )

    async def stop_broadcast_loop(self) -> None:
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass

    async def _consume_and_broadcast(self) -> None:
        bus = get_event_bus()
        q = bus.subscribe_all()
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=1.0)
                await self.broadcast(event.topic.value, event.payload)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("websocket.broadcast.error", error=str(exc))

    @property
    def connection_count(self) -> int:
        return len(self._connections)


_manager: WebSocketManager | None = None


def get_ws_manager() -> WebSocketManager:
    global _manager
    if _manager is None:
        _manager = WebSocketManager()
    return _manager
