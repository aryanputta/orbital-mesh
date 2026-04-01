import datetime
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Any

from api.models.telemetry import TelemetryFrameResponse, TelemetryAggregateResponse
from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/telemetry", tags=["telemetry"])


def get_db_pool():
    from simulation.runner import get_runner
    runner = get_runner()
    if runner is None:
        raise HTTPException(status_code=503, detail="Simulation not running")
    return runner.db_pool


@router.get("/{node_id}", response_model=list[dict])
async def get_telemetry(
    node_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    pool=Depends(get_db_pool),
) -> list[dict]:
    if pool is None:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT time, node_id, temperature, voltage, rpm, latency_ms, packet_loss_pct, sequence_number
                FROM telemetry
                WHERE node_id = $1
                ORDER BY time DESC
                LIMIT $2
                """,
                node_id,
                limit,
            )
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.error("telemetry.query.failed", error=str(exc))
        return []


@router.get("/{node_id}/aggregate", response_model=list[dict])
async def get_aggregate(
    node_id: str,
    hours: int = Query(default=1, ge=1, le=168),
    pool=Depends(get_db_pool),
) -> list[dict]:
    if pool is None:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT
                    time_bucket('1 minute', time) AS bucket,
                    node_id,
                    AVG(temperature) AS temperature_avg,
                    MIN(temperature) AS temperature_min,
                    MAX(temperature) AS temperature_max,
                    AVG(voltage) AS voltage_avg,
                    AVG(latency_ms) AS latency_avg,
                    AVG(packet_loss_pct) AS loss_avg
                FROM telemetry
                WHERE node_id = $1 AND time >= NOW() - INTERVAL '1 hour' * $2
                GROUP BY bucket, node_id
                ORDER BY bucket DESC
                """,
                node_id,
                hours,
            )
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.error("telemetry.aggregate.failed", error=str(exc))
        return []
