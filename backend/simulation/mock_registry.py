import time
from nodes.node_registry import NodeInfo, NodeState, NodeRole
from nodes.telemetry_generator import TelemetryFrame
from protocol.decision_log import SwitchDecision
from core.logging import get_logger

logger = get_logger(__name__)


class MockRegistry:
    def __init__(self) -> None:
        self._nodes: dict[str, NodeInfo] = {}

    async def register(self, info: NodeInfo) -> None:
        info.last_seen = time.time()
        self._nodes[info.node_id] = info

    async def deregister(self, node_id: str) -> None:
        self._nodes.pop(node_id, None)

    async def heartbeat(self, node_id: str, state: NodeState, transport: str) -> None:
        if node_id in self._nodes:
            self._nodes[node_id].state = state
            self._nodes[node_id].current_transport = transport
            self._nodes[node_id].last_seen = time.time()

    async def get(self, node_id: str) -> NodeInfo | None:
        return self._nodes.get(node_id)

    async def get_all(self) -> list[NodeInfo]:
        return list(self._nodes.values())

    async def update_state(self, node_id: str, state: NodeState) -> None:
        if node_id in self._nodes:
            self._nodes[node_id].state = state

    async def get_state(self, node_id: str) -> NodeState | None:
        n = self._nodes.get(node_id)
        return n.state if n else None

    async def get_by_role(self, role: NodeRole) -> list[NodeInfo]:
        return [n for n in self._nodes.values() if n.role == role]


class MockProducer:
    async def publish(self, frame: TelemetryFrame) -> None:
        pass

    async def publish_event(self, event_type: str, payload: dict) -> None:
        pass

    async def get_stream_length(self, node_id: str) -> int:
        return 0


class MockDecisionLog:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def log_decision(self, decision: SwitchDecision) -> None:
        logger.info(
            "protocol.switch",
            node_id=decision.node_id,
            from_t=decision.from_transport.value,
            to_t=decision.to_transport.value,
        )


class MockWriter:
    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def write_telemetry(self, frame: dict) -> None:
        pass

    async def write_anomaly(self, event: dict) -> None:
        pass

    async def write_failover(self, event: dict) -> None:
        pass
