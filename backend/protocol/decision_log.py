import asyncio
import time
from dataclasses import dataclass

import asyncpg

from network.base_transport import TransportType
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SwitchDecision:
    node_id: str
    from_transport: TransportType
    to_transport: TransportType
    reason: str
    rtt_before: float
    loss_before: float
    rtt_after: float
    loss_after: float
    timestamp: float


class DecisionLog:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._buffer: list[SwitchDecision] = []
        self._flush_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def stop(self) -> None:
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        if self._buffer:
            await self._flush()

    async def log_decision(self, decision: SwitchDecision) -> None:
        self._buffer.append(decision)
        logger.info(
            "protocol.switch",
            node_id=decision.node_id,
            from_transport=decision.from_transport.value,
            to_transport=decision.to_transport.value,
            reason=decision.reason,
            rtt_before=decision.rtt_before,
            rtt_after=decision.rtt_after,
        )

    async def _flush_loop(self) -> None:
        while True:
            await asyncio.sleep(2.0)
            if self._buffer:
                await self._flush()

    async def _flush(self) -> None:
        if not self._buffer:
            return
        batch = self._buffer[:]
        self._buffer.clear()
        try:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO protocol_switches
                        (time, node_id, from_transport, to_transport, reason, rtt_before, rtt_after)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    [
                        (
                            _ts_to_datetime(d.timestamp),
                            d.node_id,
                            d.from_transport.value,
                            d.to_transport.value,
                            d.reason,
                            d.rtt_before,
                            d.rtt_after,
                        )
                        for d in batch
                    ],
                )
        except Exception as exc:
            logger.error("decision_log.flush.failed", error=str(exc))
            self._buffer = batch + self._buffer


def _ts_to_datetime(ts: float):
    import datetime
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
