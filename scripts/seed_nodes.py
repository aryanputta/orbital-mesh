#!/usr/bin/env python3
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import redis.asyncio as aioredis

from nodes.node_registry import NodeRegistry, NodeInfo, NodeRole, NodeState
from core.config import get_settings


async def seed() -> None:
    settings = get_settings()
    redis = aioredis.from_url(settings.redis_url, decode_responses=False)
    registry = NodeRegistry(redis)

    nodes = [
        NodeInfo(
            node_id="node-00",
            role=NodeRole.COORDINATOR,
            host="127.0.0.1",
            tcp_port=9000,
            udp_port=9100,
            quic_port=9200,
            control_port=9500,
            state=NodeState.ONLINE,
            peer_ids=["node-01", "node-02", "node-03"],
        ),
        NodeInfo(
            node_id="node-01",
            role=NodeRole.COORDINATOR,
            host="127.0.0.1",
            tcp_port=9001,
            udp_port=9101,
            quic_port=9201,
            control_port=9501,
            state=NodeState.ONLINE,
            peer_ids=["node-00", "node-04", "node-05"],
        ),
    ]

    for i in range(2, 5):
        nodes.append(NodeInfo(
            node_id=f"node-{i:02d}",
            role=NodeRole.RELAY,
            host="127.0.0.1",
            tcp_port=9000 + i,
            udp_port=9100 + i,
            quic_port=9200 + i,
            control_port=9500 + i,
            state=NodeState.ONLINE,
            peer_ids=[f"node-{j:02d}" for j in range(max(0, i - 2), min(10, i + 3)) if j != i],
        ))

    for i in range(5, 10):
        nodes.append(NodeInfo(
            node_id=f"node-{i:02d}",
            role=NodeRole.LEAF,
            host="127.0.0.1",
            tcp_port=9000 + i,
            udp_port=9100 + i,
            quic_port=9200 + i,
            control_port=9500 + i,
            state=NodeState.ONLINE,
            peer_ids=[f"node-{i - 1:02d}", f"node-{(i - 3) % 10:02d}"],
        ))

    for node in nodes:
        await registry.register(node)
        print(f"Seeded {node.node_id} ({node.role.value})")

    await redis.aclose()
    print(f"\nSeeded {len(nodes)} nodes into Redis at {settings.redis_url}")


if __name__ == "__main__":
    asyncio.run(seed())
