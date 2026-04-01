import json
import time
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any

import redis.asyncio as aioredis

from core.logging import get_logger

logger = get_logger(__name__)

REGISTRY_KEY = "orbital:nodes"
NODE_KEY_PREFIX = "orbital:node:"
TTL_S = 120


class NodeRole(str, Enum):
    COORDINATOR = "coordinator"
    RELAY = "relay"
    LEAF = "leaf"


class NodeState(str, Enum):
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    RECOVERING = "recovering"


@dataclass
class NodeInfo:
    node_id: str
    role: NodeRole
    host: str
    tcp_port: int
    udp_port: int
    quic_port: int
    control_port: int
    state: NodeState = NodeState.OFFLINE
    current_transport: str = "tcp"
    last_seen: float = 0.0
    peer_ids: list[str] = None

    def __post_init__(self):
        if self.peer_ids is None:
            self.peer_ids = []

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["role"] = self.role.value
        d["state"] = self.state.value
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NodeInfo":
        data["role"] = NodeRole(data["role"])
        data["state"] = NodeState(data["state"])
        return cls(**data)


class NodeRegistry:
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    async def register(self, info: NodeInfo) -> None:
        info.last_seen = time.time()
        key = f"{NODE_KEY_PREFIX}{info.node_id}"
        data = json.dumps(info.to_dict())
        await self._redis.set(key, data, ex=TTL_S)
        await self._redis.sadd(REGISTRY_KEY, info.node_id)
        logger.info("registry.registered", node_id=info.node_id, role=info.role.value)

    async def deregister(self, node_id: str) -> None:
        await self._redis.delete(f"{NODE_KEY_PREFIX}{node_id}")
        await self._redis.srem(REGISTRY_KEY, node_id)
        logger.info("registry.deregistered", node_id=node_id)

    async def heartbeat(self, node_id: str, state: NodeState, transport: str) -> None:
        key = f"{NODE_KEY_PREFIX}{node_id}"
        data = await self._redis.get(key)
        if data:
            info = NodeInfo.from_dict(json.loads(data))
            info.last_seen = time.time()
            info.state = state
            info.current_transport = transport
            await self._redis.set(key, json.dumps(info.to_dict()), ex=TTL_S)

    async def get(self, node_id: str) -> NodeInfo | None:
        data = await self._redis.get(f"{NODE_KEY_PREFIX}{node_id}")
        if not data:
            return None
        return NodeInfo.from_dict(json.loads(data))

    async def get_all(self) -> list[NodeInfo]:
        node_ids = await self._redis.smembers(REGISTRY_KEY)
        nodes = []
        for nid in node_ids:
            info = await self.get(nid.decode() if isinstance(nid, bytes) else nid)
            if info:
                nodes.append(info)
        return nodes

    async def update_state(self, node_id: str, state: NodeState) -> None:
        key = f"{NODE_KEY_PREFIX}{node_id}"
        data = await self._redis.get(key)
        if data:
            info = NodeInfo.from_dict(json.loads(data))
            info.state = state
            info.last_seen = time.time()
            await self._redis.set(key, json.dumps(info.to_dict()), ex=TTL_S)

    async def get_state(self, node_id: str) -> NodeState | None:
        info = await self.get(node_id)
        return info.state if info else None

    async def get_by_role(self, role: NodeRole) -> list[NodeInfo]:
        all_nodes = await self.get_all()
        return [n for n in all_nodes if n.role == role]
