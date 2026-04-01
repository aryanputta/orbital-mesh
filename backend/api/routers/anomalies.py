from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/anomalies", tags=["anomalies"])


def get_db_pool():
    from simulation.runner import get_runner
    runner = get_runner()
    if runner is None:
        raise HTTPException(status_code=503, detail="Simulation not running")
    return runner.db_pool


@router.get("/")
async def list_anomalies(
    node_id: str | None = Query(default=None),
    failure_class: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    pool=Depends(get_db_pool),
) -> list[dict]:
    if pool is None:
        return []
    conditions = ["1=1"]
    params: list[Any] = []
    idx = 1

    if node_id:
        conditions.append(f"node_id = ${idx}")
        params.append(node_id)
        idx += 1
    if failure_class:
        conditions.append(f"failure_class = ${idx}")
        params.append(failure_class)
        idx += 1

    params.append(limit)
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, time, node_id, anomaly_score, failure_class, confidence
                FROM anomaly_events
                WHERE {' AND '.join(conditions)}
                ORDER BY time DESC
                LIMIT ${idx}
                """,
                *params,
            )
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.error("anomalies.query.failed", error=str(exc))
        return []


@router.get("/summary")
async def anomaly_summary(pool=Depends(get_db_pool)) -> dict[str, int]:
    if pool is None:
        return {}
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT failure_class, COUNT(*) as count
                FROM anomaly_events
                WHERE time >= NOW() - INTERVAL '1 hour'
                GROUP BY failure_class
                ORDER BY count DESC
                """
            )
        return {r["failure_class"]: r["count"] for r in rows}
    except Exception as exc:
        logger.error("anomalies.summary.failed", error=str(exc))
        return {}
