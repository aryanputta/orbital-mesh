import asyncio
import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from core.events import get_event_bus, EventTopic
from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/control", tags=["control"])


class GlobalFailureRequest(BaseModel):
    node_id: str
    failure_mode: str
    duration_s: float = 10.0
    intensity: float = 1.0


def get_injector():
    from simulation.runner import get_runner
    runner = get_runner()
    if runner is None:
        raise HTTPException(status_code=503, detail="Simulation not running")
    return runner.failure_injector


def get_coordinator():
    from simulation.runner import get_runner
    runner = get_runner()
    if runner is None:
        raise HTTPException(status_code=503, detail="Simulation not running")
    return runner.coordinator


@router.post("/inject-failure")
async def inject_failure(
    body: GlobalFailureRequest,
    injector=Depends(get_injector),
) -> dict[str, Any]:
    from nodes.failure_injector import FailureMode
    try:
        mode = FailureMode(body.failure_mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown failure mode: {body.failure_mode}")

    await injector.inject(body.node_id, mode, body.duration_s, body.intensity)
    return {"status": "injected", "node_id": body.node_id, "mode": body.failure_mode}


@router.get("/system-state")
async def system_state(coordinator=Depends(get_coordinator)) -> dict:
    return coordinator.system_state()


@router.get("/failover-history")
async def failover_history(coordinator=Depends(get_coordinator)) -> list[dict]:
    from simulation.runner import get_runner
    runner = get_runner()
    if runner and runner.failover_handler:
        return runner.failover_handler.get_history()
    return []


@router.get("/reroute-history")
async def reroute_history() -> list[dict]:
    from simulation.runner import get_runner
    runner = get_runner()
    if runner and runner.rerouter:
        return runner.rerouter.get_history()
    return []


@router.get("/events")
async def event_stream():
    bus = get_event_bus()
    q = bus.subscribe_all()

    async def generator():
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=15.0)
                yield {
                    "event": event.topic.value,
                    "data": str(event.payload),
                    "id": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(),
                }
            except asyncio.TimeoutError:
                yield {"event": "ping", "data": "keepalive"}
            except asyncio.CancelledError:
                bus.unsubscribe_all(q)
                return

    return EventSourceResponse(generator())
