from fastapi import APIRouter, HTTPException, Depends
from typing import Any

from api.models.node import NodeInfoResponse, FailureInjectionRequest
from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/nodes", tags=["nodes"])


def get_registry():
    from simulation.runner import get_runner
    runner = get_runner()
    if runner is None:
        raise HTTPException(status_code=503, detail="Simulation not running")
    return runner.registry


def get_injector():
    from simulation.runner import get_runner
    runner = get_runner()
    if runner is None:
        raise HTTPException(status_code=503, detail="Simulation not running")
    return runner.failure_injector


@router.get("/", response_model=list[NodeInfoResponse])
async def list_nodes(registry=Depends(get_registry)):
    nodes = await registry.get_all()
    return [NodeInfoResponse(**n.to_dict()) for n in nodes]


@router.get("/{node_id}", response_model=NodeInfoResponse)
async def get_node(node_id: str, registry=Depends(get_registry)):
    node = await registry.get(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    return NodeInfoResponse(**node.to_dict())


@router.post("/{node_id}/inject-failure")
async def inject_failure(
    node_id: str,
    body: FailureInjectionRequest,
    injector=Depends(get_injector),
) -> dict[str, Any]:
    from nodes.failure_injector import FailureMode
    try:
        mode = FailureMode(body.failure_mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown failure mode: {body.failure_mode}")

    await injector.inject(node_id, mode, body.duration_s, body.intensity)
    return {"status": "injected", "node_id": node_id, "mode": body.failure_mode}


@router.post("/{node_id}/recover")
async def recover_node(node_id: str, injector=Depends(get_injector)) -> dict[str, Any]:
    await injector.restore(node_id)
    return {"status": "restored", "node_id": node_id}


@router.get("/{node_id}/failures")
async def active_failures(injector=Depends(get_injector)) -> list[dict]:
    return injector.active_failures()
