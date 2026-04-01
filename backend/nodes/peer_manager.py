import asyncio
import time
from typing import Any

from network.base_transport import BaseTransport, TransportType
from network.tcp_transport import TCPTransport, TCPConnection
from core.logging import get_logger
import msgpack

logger = get_logger(__name__)

MAX_BACKOFF_S = 60.0
INITIAL_BACKOFF_S = 1.0


class PeerManager:
    def __init__(self, node_id: str) -> None:
        self._node_id = node_id
        self._peers: dict[str, BaseTransport] = {}
        self._peer_addrs: dict[str, tuple[str, int]] = {}
        self._reconnect_tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def add_peer(self, peer_id: str, transport: BaseTransport, addr: tuple[str, int]) -> None:
        async with self._lock:
            self._peers[peer_id] = transport
            self._peer_addrs[peer_id] = addr
        logger.info("peer.added", node_id=self._node_id, peer_id=peer_id)

    async def remove_peer(self, peer_id: str) -> None:
        async with self._lock:
            transport = self._peers.pop(peer_id, None)
            self._peer_addrs.pop(peer_id, None)
        if transport:
            await transport.close()
        logger.info("peer.removed", node_id=self._node_id, peer_id=peer_id)

    async def send_to_peer(self, peer_id: str, message: dict[str, Any]) -> bool:
        transport = self._peers.get(peer_id)
        if not transport or not transport.connected:
            self._schedule_reconnect(peer_id)
            return False
        try:
            data = msgpack.packb(message, use_bin_type=True)
            await transport.send(data)
            return True
        except (ConnectionError, Exception) as exc:
            logger.warning("peer.send.failed", peer_id=peer_id, error=str(exc))
            self._schedule_reconnect(peer_id)
            return False

    async def broadcast(self, message: dict[str, Any]) -> dict[str, bool]:
        results: dict[str, bool] = {}
        tasks = {
            peer_id: asyncio.create_task(self.send_to_peer(peer_id, message))
            for peer_id in list(self._peers.keys())
        }
        for peer_id, task in tasks.items():
            try:
                results[peer_id] = await task
            except Exception:
                results[peer_id] = False
        return results

    def connected_peers(self) -> list[str]:
        return [pid for pid, t in self._peers.items() if t.connected]

    def all_peers(self) -> list[str]:
        return list(self._peers.keys())

    def _schedule_reconnect(self, peer_id: str) -> None:
        if peer_id in self._reconnect_tasks and not self._reconnect_tasks[peer_id].done():
            return
        task = asyncio.create_task(self._reconnect_with_backoff(peer_id))
        self._reconnect_tasks[peer_id] = task

    async def _reconnect_with_backoff(self, peer_id: str) -> None:
        backoff = INITIAL_BACKOFF_S
        while True:
            addr = self._peer_addrs.get(peer_id)
            if not addr:
                return
            await asyncio.sleep(backoff)
            try:
                tcp = TCPTransport()
                conn = await tcp.connect(addr[0], addr[1])
                await self.add_peer(peer_id, conn, addr)
                logger.info("peer.reconnected", peer_id=peer_id)
                return
            except Exception as exc:
                logger.warning("peer.reconnect.failed", peer_id=peer_id, error=str(exc), backoff=backoff)
                backoff = min(backoff * 2, MAX_BACKOFF_S)

    async def close_all(self) -> None:
        for task in self._reconnect_tasks.values():
            task.cancel()
        for transport in self._peers.values():
            try:
                await transport.close()
            except Exception:
                pass
        self._peers.clear()
