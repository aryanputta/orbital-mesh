import asyncio
from dataclasses import dataclass, field

import networkx as nx

from core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EdgeAttributes:
    transport: str
    rtt_ms: float
    loss_rate: float
    throughput_bps: float


@dataclass
class TopologySnapshot:
    nodes: list[dict]
    edges: list[dict]

    def to_dict(self) -> dict:
        return {"nodes": self.nodes, "edges": self.edges}


class TopologyManager:
    def __init__(self) -> None:
        self._graph = nx.DiGraph()
        self._lock = asyncio.Lock()

    async def add_node(self, node_id: str, role: str, state: str) -> None:
        async with self._lock:
            self._graph.add_node(node_id, role=role, state=state)

    async def remove_node(self, node_id: str) -> None:
        async with self._lock:
            if self._graph.has_node(node_id):
                self._graph.remove_node(node_id)

    async def update_node(self, node_id: str, **attrs) -> None:
        async with self._lock:
            if self._graph.has_node(node_id):
                self._graph.nodes[node_id].update(attrs)

    async def add_edge(
        self,
        src: str,
        dst: str,
        transport: str,
        rtt_ms: float,
        loss_rate: float = 0.0,
        throughput_bps: float = 0.0,
    ) -> None:
        async with self._lock:
            weight = max(rtt_ms, 0.001)
            self._graph.add_edge(
                src,
                dst,
                transport=transport,
                rtt_ms=rtt_ms,
                loss_rate=loss_rate,
                throughput_bps=throughput_bps,
                weight=weight,
            )

    async def remove_edge(self, src: str, dst: str) -> None:
        async with self._lock:
            if self._graph.has_edge(src, dst):
                self._graph.remove_edge(src, dst)

    async def get_shortest_path(self, src: str, dst: str) -> list[str]:
        async with self._lock:
            try:
                path = nx.shortest_path(self._graph, src, dst, weight="weight")
                return path
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                return []

    async def get_all_paths(self, src: str, dst: str, cutoff: int = 5) -> list[list[str]]:
        async with self._lock:
            try:
                paths = list(nx.all_simple_paths(self._graph, src, dst, cutoff=cutoff))
                return paths
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                return []

    async def get_snapshot(self) -> TopologySnapshot:
        async with self._lock:
            nodes = [
                {"id": n, **self._graph.nodes[n]}
                for n in self._graph.nodes
            ]
            edges = [
                {"source": u, "target": v, **self._graph.edges[u, v]}
                for u, v in self._graph.edges
            ]
            return TopologySnapshot(nodes=nodes, edges=edges)

    async def mark_node_offline(self, node_id: str) -> None:
        await self.update_node(node_id, state="offline")
        async with self._lock:
            edges_to_remove = [
                (u, v)
                for u, v in list(self._graph.edges)
                if u == node_id or v == node_id
            ]
        for u, v in edges_to_remove:
            await self.remove_edge(u, v)
        logger.info("topology.node_offline", node_id=node_id, removed_edges=len(edges_to_remove))

    async def get_neighbors(self, node_id: str) -> list[str]:
        async with self._lock:
            if not self._graph.has_node(node_id):
                return []
            return list(self._graph.neighbors(node_id))

    async def node_count(self) -> int:
        return self._graph.number_of_nodes()

    async def edge_count(self) -> int:
        return self._graph.number_of_edges()
