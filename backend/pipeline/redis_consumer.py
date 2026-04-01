import asyncio
import socket
from typing import Callable, Awaitable, Any

import msgpack
import redis.asyncio as aioredis

from core.logging import get_logger

logger = get_logger(__name__)

GROUP_NAME = "orbital-consumers"
EVENTS_STREAM = "orbital:events"
BLOCK_MS = 100
BATCH_SIZE = 100


MessageCallback = Callable[[str, dict], Awaitable[None]]


class RedisConsumer:
    def __init__(self, redis_client: aioredis.Redis, stream_keys: list[str]) -> None:
        self._redis = redis_client
        self._stream_keys = stream_keys
        self._consumer_name = f"consumer-{socket.gethostname()}"
        self._callback: MessageCallback | None = None
        self._task: asyncio.Task | None = None

    def on_message(self, callback: MessageCallback) -> None:
        self._callback = callback

    async def start(self) -> None:
        await self._ensure_groups()
        self._task = asyncio.create_task(self._consume_loop(), name="redis_consumer.loop")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _ensure_groups(self) -> None:
        for key in self._stream_keys:
            try:
                await self._redis.xgroup_create(key, GROUP_NAME, id="0", mkstream=True)
                logger.info("redis_consumer.group_created", stream=key)
            except aioredis.ResponseError as exc:
                if "BUSYGROUP" not in str(exc):
                    logger.warning("redis_consumer.group_error", stream=key, error=str(exc))

    async def _consume_loop(self) -> None:
        streams = {key: ">" for key in self._stream_keys}
        while True:
            try:
                results = await self._redis.xreadgroup(
                    GROUP_NAME,
                    self._consumer_name,
                    streams,
                    count=BATCH_SIZE,
                    block=BLOCK_MS,
                )
                if results:
                    for stream_key, messages in results:
                        key = stream_key.decode() if isinstance(stream_key, bytes) else stream_key
                        for msg_id, fields in messages:
                            await self._process_message(key, msg_id, fields)
            except aioredis.ResponseError as exc:
                if "NOGROUP" in str(exc):
                    await self._ensure_groups()
                else:
                    logger.error("redis_consumer.error", error=str(exc))
                    await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("redis_consumer.loop.error", error=str(exc))
                await asyncio.sleep(1.0)

    async def _process_message(self, stream_key: str, msg_id, fields: dict) -> None:
        raw = fields.get(b"data") or fields.get("data")
        if not raw:
            return
        try:
            payload = msgpack.unpackb(raw, raw=False)
            if self._callback:
                await self._callback(stream_key, payload)
            await self._redis.xack(stream_key, GROUP_NAME, msg_id)
        except Exception as exc:
            logger.error("redis_consumer.process.error", stream=stream_key, error=str(exc))
