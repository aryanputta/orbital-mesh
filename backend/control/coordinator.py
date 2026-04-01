import asyncio
import time
from typing import Any

from control.topology_manager import TopologyManager
from control.rerouter import Rerouter
from control.failover_handler import FailoverHandler
from nodes.node_registry import NodeRegistry, NodeState
from core.events import get_event_bus, EventTopic, Event
from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)


class Coordinator:
    def __init__(
        self,
        registry: NodeRegistry,
        topology: TopologyManager,
        rerouter: Rerouter,
        failover: FailoverHandler,
    ) -> None:
        self._registry = registry
        self._topology = topology
        self._rerouter = rerouter
        self._failover = failover
        self._settings = get_settings()
        self._tasks: list[asyncio.Task] = []
        self._node_last_seen: dict[str, float] = {}
        self._system_state: dict[str, Any] = {
            "status": "initializing",
            "uptime_s": 0,
            "started_at": time.time(),
        }

    async def start(self) -> None:
        bus = get_event_bus()
        self._tasks = [
            asyncio.create_task(self._consume_events(bus), name="coordinator.events"),
            asyncio.create_task(self._health_monitor(), name="coordinator.health"),
            asyncio.create_task(self._topology_sync(), name="coordinator.topology_sync"),
        ]
        self._system_state["status"] = "running"
        logger.info("coordinator.started")

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        logger.info("coordinator.stopped")

    def system_state(self) -> dict:
        state = dict(self._system_state)
        state["uptime_s"] = time.time() - self._system_state["started_at"]
        return state

    async def _consume_events(self, bus) -> None:
        q = bus.subscribe_all()
        while True:
            try:
                event: Event = await asyncio.wait_for(q.get(), timeout=1.0)
                await self._dispatch(event)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("coordinator.event.error", error=str(exc))

    async def _dispatch(self, event: Event) -> None:
        if event.topic == EventTopic.NODE_FAILED:
            await self._on_node_failed(event.payload)
        elif event.topic == EventTopic.HEARTBEAT:
            await self._on_heartbeat(event.payload)
        elif event.topic == EventTopic.ANOMALY_DETECTED:
            await self._on_anomaly(event.payload)
        elif event.topic == EventTopic.PROTOCOL_SWITCHED:
            await self._on_protocol_switched(event.payload)

    async def _on_node_failed(self, payload: dict) -> None:
        node_id = payload.get("node_id")
        if not node_id:
            return
        failure_mode = payload.get("failure_mode", "unknown")
        logger.warning("coordinator.node_failed", node_id=node_id, mode=failure_mode)
        await self._failover.handle_suspected_crash(node_id)

    async def _on_heartbeat(self, payload: dict) -> None:
        node_id = payload.get("node_id")
        if node_id:
            self._node_last_seen[node_id] = time.monotonic()

    async def _on_anomaly(self, payload: dict) -> None:
        node_id = payload.get("node_id")
        score = payload.get("anomaly_score", 0.0)
        failure_class = payload.get("failure_class", "unknown")
        logger.warning(
            "coordinator.anomaly",
            node_id=node_id,
            score=score,
            failure_class=failure_class,
        )

    async def _on_protocol_switched(self, payload: dict) -> None:
        node_id = payload.get("node_id")
        from_t = payload.get("from")
        to_t = payload.get("to")
        await self._topology.update_node(node_id, transport=to_t) if node_id else None
        logger.info("coordinator.protocol_switch", node_id=node_id, from_t=from_t, to_t=to_t)

    async def _health_monitor(self) -> None:
        timeout = self._settings.node_offline_timeout_s
        while True:
            await asyncio.sleep(10.0)
            now = time.monotonic()
            try:
                all_nodes = await self._registry.get_all()
                for node in all_nodes:
                    last = self._node_last_seen.get(node.node_id, now)
                    if now - last > timeout and node.state != NodeState.OFFLINE:
                        logger.warning("coordinator.node_timeout", node_id=node.node_id)
                        await self._registry.update_state(node.node_id, NodeState.OFFLINE)
                        await self._failover.handle_suspected_crash(node.node_id)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("coordinator.health_monitor.error", error=str(exc))

    async def _topology_sync(self) -> None:
        while True:
            await asyncio.sleep(5.0)
            try:
                all_nodes = await self._registry.get_all()
                for node in all_nodes:
                    await self._topology.update_node(
                        node.node_id,
                        state=node.state.value,
                        transport=node.current_transport,
                    )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("coordinator.topology_sync.error", error=str(exc))
