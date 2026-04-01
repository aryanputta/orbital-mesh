import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nodes.node_registry import NodeInfo, NodeRole


@dataclass
class NetworkScenario:
    name: str
    description: str
    node_count: int
    topology: str
    loss_rate: float
    jitter_ms_max: float
    base_delay_ms: float
    bandwidth_limit_bps: float | None


BUILTIN_SCENARIOS: dict[str, NetworkScenario] = {
    "normal": NetworkScenario(
        name="normal",
        description="Stable network conditions",
        node_count=10,
        topology="mesh",
        loss_rate=0.005,
        jitter_ms_max=5.0,
        base_delay_ms=2.0,
        bandwidth_limit_bps=None,
    ),
    "degraded": NetworkScenario(
        name="degraded",
        description="High latency, moderate packet loss",
        node_count=10,
        topology="mesh",
        loss_rate=0.08,
        jitter_ms_max=80.0,
        base_delay_ms=50.0,
        bandwidth_limit_bps=500_000,
    ),
    "congested": NetworkScenario(
        name="congested",
        description="Severe congestion with bandwidth constraints",
        node_count=10,
        topology="ring",
        loss_rate=0.15,
        jitter_ms_max=200.0,
        base_delay_ms=100.0,
        bandwidth_limit_bps=100_000,
    ),
    "satellite": NetworkScenario(
        name="satellite",
        description="High-latency satellite link simulation",
        node_count=8,
        topology="star",
        loss_rate=0.02,
        jitter_ms_max=30.0,
        base_delay_ms=250.0,
        bandwidth_limit_bps=250_000,
    ),
}


def load_scenario(name: str) -> NetworkScenario:
    if name in BUILTIN_SCENARIOS:
        return BUILTIN_SCENARIOS[name]
    raise ValueError(f"Unknown scenario: {name}. Available: {list(BUILTIN_SCENARIOS)}")


def build_node_infos(
    node_count: int,
    base_tcp_port: int,
    base_udp_port: int,
    base_quic_port: int,
    control_port_offset: int,
    host: str = "0.0.0.0",
) -> tuple[list[NodeInfo], list[tuple[str, str]]]:
    nodes: list[NodeInfo] = []
    coordinator_count = max(1, node_count // 5)
    relay_count = max(2, node_count // 3)

    for i in range(node_count):
        if i < coordinator_count:
            role = NodeRole.COORDINATOR
        elif i < coordinator_count + relay_count:
            role = NodeRole.RELAY
        else:
            role = NodeRole.LEAF

        node_id = f"node-{i:02d}"
        nodes.append(NodeInfo(
            node_id=node_id,
            role=role,
            host=host,
            tcp_port=base_tcp_port + i,
            udp_port=base_udp_port + i,
            quic_port=base_quic_port + i,
            control_port=base_tcp_port + i + control_port_offset,
        ))

    edges = _build_edges(nodes)
    return nodes, edges


def _build_edges(nodes: list[NodeInfo]) -> list[tuple[str, str]]:
    edges: list[tuple[str, str]] = []
    ids = [n.node_id for n in nodes]
    n = len(ids)

    if n <= 1:
        return edges

    for i in range(n):
        next_i = (i + 1) % n
        if ids[i] != ids[next_i]:
            edges.append((ids[i], ids[next_i]))

    extra = max(0, n // 3)
    for _ in range(extra):
        src, dst = random.sample(ids, 2)
        if (src, dst) not in edges and (dst, src) not in edges:
            edges.append((src, dst))

    return edges
