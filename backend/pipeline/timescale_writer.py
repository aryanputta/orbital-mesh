import asyncio
import datetime
from typing import Any

import asyncpg

from core.logging import get_logger

logger = get_logger(__name__)

FLUSH_INTERVAL_S = 0.5
MAX_BATCH_SIZE = 100


class TimescaleWriter:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool
        self._telemetry_buffer: list[dict] = []
        self._anomaly_buffer: list[dict] = []
        self._failover_buffer: list[dict] = []
        self._lock = asyncio.Lock()
        self._flush_task: asyncio.Task | None = None

    async def start(self) -> None:
        self._flush_task = asyncio.create_task(self._flush_loop(), name="timescale_writer.flush")

    async def stop(self) -> None:
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self._flush_all()

    async def write_telemetry(self, frame: dict) -> None:
        async with self._lock:
            self._telemetry_buffer.append(frame)
            if len(self._telemetry_buffer) >= MAX_BATCH_SIZE:
                await self._flush_telemetry()

    async def write_anomaly(self, event: dict) -> None:
        async with self._lock:
            self._anomaly_buffer.append(event)

    async def write_failover(self, event: dict) -> None:
        async with self._lock:
            self._failover_buffer.append(event)

    async def _flush_loop(self) -> None:
        while True:
            await asyncio.sleep(FLUSH_INTERVAL_S)
            await self._flush_all()

    async def _flush_all(self) -> None:
        async with self._lock:
            await self._flush_telemetry()
            await self._flush_anomalies()
            await self._flush_failovers()

    async def _flush_telemetry(self) -> None:
        if not self._telemetry_buffer:
            return
        batch = self._telemetry_buffer[:]
        self._telemetry_buffer.clear()
        try:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO telemetry
                        (time, node_id, temperature, voltage, rpm, latency_ms, packet_loss_pct, sequence_number)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    ON CONFLICT DO NOTHING
                    """,
                    [
                        (
                            _parse_ts(r["timestamp"]),
                            r["node_id"],
                            r.get("temperature_c"),
                            r.get("voltage_v"),
                            r.get("rpm"),
                            r.get("latency_ms"),
                            r.get("packet_loss_pct"),
                            r.get("sequence_number"),
                        )
                        for r in batch
                    ],
                )
        except Exception as exc:
            logger.error("timescale.flush_telemetry.failed", error=str(exc), count=len(batch))
            self._telemetry_buffer = batch + self._telemetry_buffer

    async def _flush_anomalies(self) -> None:
        if not self._anomaly_buffer:
            return
        batch = self._anomaly_buffer[:]
        self._anomaly_buffer.clear()
        try:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO anomaly_events
                        (time, node_id, anomaly_score, failure_class, confidence)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    [
                        (
                            _parse_ts(r.get("timestamp")),
                            r.get("node_id"),
                            r.get("anomaly_score"),
                            r.get("failure_class"),
                            r.get("confidence"),
                        )
                        for r in batch
                    ],
                )
        except Exception as exc:
            logger.error("timescale.flush_anomalies.failed", error=str(exc))
            self._anomaly_buffer = batch + self._anomaly_buffer

    async def _flush_failovers(self) -> None:
        if not self._failover_buffer:
            return
        batch = self._failover_buffer[:]
        self._failover_buffer.clear()
        try:
            async with self._pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO failover_events
                        (time, failed_node, rerouted_via, duration_ms)
                    VALUES ($1, $2, $3, $4)
                    """,
                    [
                        (
                            datetime.datetime.now(tz=datetime.timezone.utc),
                            r.get("failed_node"),
                            r.get("rerouted_via", []),
                            r.get("duration_ms"),
                        )
                        for r in batch
                    ],
                )
        except Exception as exc:
            logger.error("timescale.flush_failovers.failed", error=str(exc))
            self._failover_buffer = batch + self._failover_buffer


def _parse_ts(ts_str: str | None) -> datetime.datetime:
    if ts_str:
        try:
            return datetime.datetime.fromisoformat(ts_str)
        except ValueError:
            pass
    return datetime.datetime.now(tz=datetime.timezone.utc)
