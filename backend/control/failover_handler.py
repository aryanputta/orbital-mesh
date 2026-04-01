import asyncio
import time
from dataclasses import dataclass

from control.topology_manager import TopologyManager
from control.rerouter import Rerouter
from nodes.node_registry import NodeRegistry, NodeState, NodeRole
from core.events import get_event_bus, EventTopic
from core.logging import get_logger

logger = get_logger(__name__)

CRASH_CONFIRM_DELAY_S = 5.0


@dataclass
class FailoverRecord:
    failed_node_id: str
    triggered_at: float
    confirmed_at: float | None = None
    recovery_started_at: float | None = None
    recovery_completed_at: float | None = None
    new_coordinator: str | None = None


class FailoverHandler:
    def __init__(
        self,
        topology: TopologyManager,
        rerouter: Rerouter,
        registry: NodeRegistry,
    ) -> None:
        self._topology = topology
        self._rerouter = rerouter
        self._registry = registry
        self._pending: dict[str, asyncio.Task] = {}
        self._history: list[FailoverRecord] = []

    async def handle_suspected_crash(self, node_id: str) -> None:
        if node_id in self._pending:
            return
        task = asyncio.create_task(self._confirm_and_failover(node_id))
        self._pending[node_id] = task

    async def _confirm_and_failover(self, node_id: str) -> None:
        record = FailoverRecord(failed_node_id=node_id, triggered_at=time.time())

        await asyncio.sleep(CRASH_CONFIRM_DELAY_S)

        state = await self._registry.get_state(node_id)
        if state not in (NodeState.OFFLINE, NodeState.DEGRADED):
            logger.info("failover.false_positive", node_id=node_id, state=state)
            self._pending.pop(node_id, None)
            return

        record.confirmed_at = time.time()
        record.recovery_started_at = time.time()
        self._history.append(record)

        logger.info("failover.confirmed", node_id=node_id)

        await get_event_bus().publish(
            EventTopic.FAILOVER_TRIGGERED,
            {
                "failed_node": node_id,
                "triggered_at": record.triggered_at,
                "confirmed_at": record.confirmed_at,
            },
        )

        await self._rerouter.reroute(node_id)

        node_info = await self._registry.get(node_id)
        if node_info and node_info.role == NodeRole.COORDINATOR:
            new_coordinator = await self._elect_new_coordinator(node_id)
            record.new_coordinator = new_coordinator

        record.recovery_completed_at = time.time()
        self._pending.pop(node_id, None)

    async def _elect_new_coordinator(self, failed_coordinator_id: str) -> str | None:
        relay_nodes = await self._registry.get_by_role(NodeRole.RELAY)
        online_relays = [
            n for n in relay_nodes
            if n.state == NodeState.ONLINE and n.node_id != failed_coordinator_id
        ]

        if not online_relays:
            logger.warning("failover.no_relay_for_coordinator_election")
            return None

        new_coord = max(online_relays, key=lambda n: n.node_id)
        logger.info("failover.new_coordinator_elected", node_id=new_coord.node_id)

        await get_event_bus().publish(
            EventTopic.CONTROL_COMMAND,
            {
                "command": "become_coordinator",
                "target_node": new_coord.node_id,
                "reason": f"coordinator_{failed_coordinator_id}_failed",
            },
        )
        return new_coord.node_id

    def get_history(self, limit: int = 20) -> list[dict]:
        records = self._history[-limit:]
        return [
            {
                "failed_node_id": r.failed_node_id,
                "triggered_at": r.triggered_at,
                "confirmed_at": r.confirmed_at,
                "recovery_started_at": r.recovery_started_at,
                "recovery_completed_at": r.recovery_completed_at,
                "new_coordinator": r.new_coordinator,
                "duration_ms": (
                    (r.recovery_completed_at - r.triggered_at) * 1000
                    if r.recovery_completed_at
                    else None
                ),
            }
            for r in reversed(records)
        ]
