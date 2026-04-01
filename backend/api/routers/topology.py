from fastapi import APIRouter, HTTPException, Depends
from typing import Any

from core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/topology", tags=["topology"])


def get_topology():
    from simulation.runner import get_runner
    runner = get_runner()
    if runner is None:
        raise HTTPException(status_code=503, detail="Simulation not running")
    return runner.topology


@router.get("/")
async def get_topology_snapshot(topology=Depends(get_topology)) -> dict:
    snapshot = await topology.get_snapshot()
    return snapshot.to_dict()


@router.get("/paths/{src}/{dst}")
async def get_path(src: str, dst: str, topology=Depends(get_topology)) -> dict[str, Any]:
    path = await topology.get_shortest_path(src, dst)
    all_paths = await topology.get_all_paths(src, dst)
    return {
        "src": src,
        "dst": dst,
        "shortest": path,
        "alternatives": all_paths[:5],
    }


@router.get("/stats")
async def topology_stats(topology=Depends(get_topology)) -> dict[str, int]:
    return {
        "nodes": await topology.node_count(),
        "edges": await topology.edge_count(),
    }
