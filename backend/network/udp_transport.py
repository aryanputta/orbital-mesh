import asyncio
import struct
import time
from typing import Callable, Awaitable

from network.base_transport import BaseTransport, TransportType
from core.logging import get_logger

UDP_HEADER_SIZE = 8
MAX_UDP_PAYLOAD = 65507

logger = get_logger(__name__)


def _pack_header(seq: int, timestamp_ms: int) -> bytes:
    return struct.pack(">II", seq & 0xFFFFFFFF, timestamp_ms & 0xFFFFFFFF)


def _unpack_header(data: bytes) -> tuple[int, int]:
    seq, ts = struct.unpack(">II", data[:UDP_HEADER_SIZE])
    return seq, ts


class UDPProtocol(asyncio.DatagramProtocol):
    def __init__(self, recv_queue: asyncio.Queue, addr_filter: tuple[str, int] | None = None) -> None:
        self._recv_queue = recv_queue
        self._addr_filter = addr_filter
        self._transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.DatagramTransport) -> None:
        self._transport = transport

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        if self._addr_filter and addr != self._addr_filter:
            return
        try:
            self._recv_queue.put_nowait((data, addr))
        except asyncio.QueueFull:
            pass

    def error_received(self, exc: Exception) -> None:
        logger.warning("udp.error", error=str(exc))

    def connection_lost(self, exc: Exception | None) -> None:
        pass

    @property
    def transport(self) -> asyncio.DatagramTransport | None:
        return self._transport


class UDPTransport(BaseTransport):
    def __init__(self) -> None:
        super().__init__(TransportType.UDP)
        self._protocol: UDPProtocol | None = None
        self._datagram_transport: asyncio.DatagramTransport | None = None
        self._recv_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        self._send_seq = 0
        self._expected_seq = 0
        self._peer_addr: tuple[str, int] | None = None

    async def bind(self, host: str, port: int) -> None:
        loop = asyncio.get_running_loop()
        self._protocol = UDPProtocol(self._recv_queue)
        self._datagram_transport, _ = await loop.create_datagram_endpoint(
            lambda: self._protocol,
            local_addr=(host, port),
        )
        self._connected = True
        logger.info("udp.bound", host=host, port=port)

    async def connect(self, host: str, port: int) -> None:
        loop = asyncio.get_running_loop()
        self._peer_addr = (host, port)
        self._protocol = UDPProtocol(self._recv_queue, addr_filter=(host, port))
        self._datagram_transport, _ = await loop.create_datagram_endpoint(
            lambda: self._protocol,
            remote_addr=(host, port),
        )
        self._connected = True
        logger.info("udp.connected", host=host, port=port)

    async def send(self, data: bytes) -> int:
        if not self._connected or not self._datagram_transport:
            raise ConnectionError("UDP transport not connected")
        if len(data) + UDP_HEADER_SIZE > MAX_UDP_PAYLOAD:
            raise ValueError(f"UDP payload too large")

        ts_ms = int(time.monotonic() * 1000) & 0xFFFFFFFF
        header = _pack_header(self._send_seq, ts_ms)
        frame = header + data
        self._send_seq += 1

        self._datagram_transport.sendto(frame)
        self._stats.bytes_sent += len(data)
        self._stats.packets_sent += 1
        return len(data)

    async def recv(self) -> bytes:
        if not self._connected:
            raise ConnectionError("UDP transport not connected")
        frame, addr = await self._recv_queue.get()
        if len(frame) < UDP_HEADER_SIZE:
            return frame

        seq, ts_ms = _unpack_header(frame)
        payload = frame[UDP_HEADER_SIZE:]

        if seq != self._expected_seq:
            dropped = (seq - self._expected_seq) % (2**32)
            self._stats.packets_dropped += dropped
        self._expected_seq = (seq + 1) % (2**32)

        now_ms = int(time.monotonic() * 1000)
        rtt_sample = (now_ms - ts_ms) & 0xFFFFFFFF
        self._stats.rtt_ms = 0.8 * self._stats.rtt_ms + 0.2 * rtt_sample

        total = self._stats.packets_recv + self._stats.packets_dropped
        if total > 0:
            self._stats.packet_loss_rate = self._stats.packets_dropped / total

        self._stats.bytes_recv += len(payload)
        self._stats.packets_recv += 1
        return payload

    async def close(self) -> None:
        self._connected = False
        if self._datagram_transport:
            self._datagram_transport.close()
            self._datagram_transport = None
