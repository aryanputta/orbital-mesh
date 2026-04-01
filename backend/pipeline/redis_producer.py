import asyncio
from typing import TYPE_CHECKING

import msgpack
import redis.asyncio as aioredis

from core.logging import get_logger

if TYPE_CHECKING:
    from nodes.telemetry_generator import TelemetryFrame

logger = get_logger(__name__)

STREAM_PREFIX = "orbital:telemetry:"
STREAM_MAXLEN = 10000
EVENTS_STREAM = "orbital:events"


class RedisProducer:
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    async def publish(self, frame: "TelemetryFrame") -> None:
        stream_key = f"{STREAM_PREFIX}{frame.node_id}"
        data = msgpack.packb(frame.to_dict(), use_bin_type=True)
        try:
            await self._redis.xadd(
                stream_key,
                {"data": data},
                maxlen=STREAM_MAXLEN,
                approximate=True,
            )
        except Exception as exc:
            logger.error("redis_producer.publish.failed", node_id=frame.node_id, error=str(exc))

    async def publish_event(self, event_type: str, payload: dict) -> None:
        data = msgpack.packb({"type": event_type, **payload}, use_bin_type=True)
        try:
            await self._redis.xadd(
                EVENTS_STREAM,
                {"data": data},
                maxlen=50000,
                approximate=True,
            )
        except Exception as exc:
            logger.error("redis_producer.event.failed", event_type=event_type, error=str(exc))

    async def get_stream_length(self, node_id: str) -> int:
        key = f"{STREAM_PREFIX}{node_id}"
        try:
            return await self._redis.xlen(key)
        except Exception:
            return 0
