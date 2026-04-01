import asyncio
import time
from dataclasses import dataclass

from control.topology_manager import TopologyManager
from core.events import get_event_bus, EventTopic
from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RerouteRecord:
    failed_node: str
    rerouted_via: list[str]
    started_at: float
    completed_at: float | None = None
    duration_ms: float | None = None


class Rerouter:
    def __init__(self, topology: TopologyManager) -> None:
        self._topology = topology
        self._history: list[RerouteRecord] = []
        self._active_reroutes: set[str] = set()

    async def reroute(self, failed_node_id: str) -> bool:
        if failed_node_id in self._active_reroutes:
            logger.info("rerouter.already_rerouting", node_id=failed_node_id)
            return False

        self._active_reroutes.add(failed_node_id)
        started_at = time.time()

        try:
            await self._topology.mark_node_offline(failed_node_id)
            affected_flows = await self._find_affected_flows(failed_node_id)
            via_nodes: list[str] = []

            for src, dst in affected_flows:
                path = await self._topology.get_shortest_path(src, dst)
                if path:
                    via_nodes.extend(path[1:-1])
                    logger.info(
                        "rerouter.path_found",
                        src=src,
                        dst=dst,
                        path=" -> ".join(path),
                    )
                else:
                    logger.warning("rerouter.no_path", src=src, dst=dst)

            completed_at = time.time()
            record = RerouteRecord(
                failed_node=failed_node_id,
                rerouted_via=list(set(via_nodes)),
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=(completed_at - started_at) * 1000,
            )
            self._history.append(record)

            await get_event_bus().publish(
                EventTopic.REROUTE_COMPLETE,
                {
                    "failed_node": failed_node_id,
                    "rerouted_via": record.rerouted_via,
                    "duration_ms": record.duration_ms,
                    "affected_flows": len(affected_flows),
                },
            )
            return True

        except Exception as exc:
            logger.error("rerouter.failed", node_id=failed_node_id, error=str(exc))
            return False
        finally:
            self._active_reroutes.discard(failed_node_id)

    def get_history(self, limit: int = 50) -> list[dict]:
        records = self._history[-limit:]
        return [
            {
                "failed_node": r.failed_node,
                "rerouted_via": r.rerouted_via,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "duration_ms": r.duration_ms,
            }
            for r in reversed(records)
        ]

    async def _find_affected_flows(self, failed_node_id: str) -> list[tuple[str, str]]:
        snapshot = await self._topology.get_snapshot()
        all_nodes = [n["id"] for n in snapshot.nodes if n["id"] != failed_node_id]
        affected = []
        for src in all_nodes:
            for dst in all_nodes:
                if src != dst:
                    affected.append((src, dst))
        return affected[:20]
