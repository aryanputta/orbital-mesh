import asyncio
import struct
import time
from typing import Callable, Awaitable

from network.base_transport import BaseTransport, TransportType
from network.congestion_control import CongestionController
from core.logging import get_logger

FRAME_HEADER_SIZE = 4
MAX_MESSAGE_SIZE = 65535

logger = get_logger(__name__)


class TCPConnection(BaseTransport):
    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        peer_addr: tuple[str, int],
    ) -> None:
        super().__init__(TransportType.TCP)
        self._reader = reader
        self._writer = writer
        self._peer_addr = peer_addr
        self._congestion = CongestionController()
        self._connected = True

    async def connect(self, host: str, port: int) -> None:
        raise RuntimeError("TCPConnection is already connected; use TCPTransport.connect() instead")

    async def send(self, data: bytes) -> int:
        if not self._connected:
            raise ConnectionError("Transport is closed")
        if len(data) > MAX_MESSAGE_SIZE:
            raise ValueError(f"Message too large: {len(data)} > {MAX_MESSAGE_SIZE}")

        frame = struct.pack(">I", len(data)) + data
        try:
            self._writer.write(frame)
            await self._writer.drain()
        except (ConnectionResetError, BrokenPipeError, OSError) as exc:
            self._connected = False
            self._congestion.on_timeout()
            raise ConnectionError(f"TCP send failed: {exc}") from exc

        self._stats.bytes_sent += len(data)
        self._stats.packets_sent += 1
        self._congestion.on_ack(len(data))
        return len(data)

    async def recv(self) -> bytes:
        if not self._connected:
            raise ConnectionError("Transport is closed")
        try:
            header = await asyncio.wait_for(
                self._reader.readexactly(FRAME_HEADER_SIZE), timeout=30.0
            )
        except asyncio.IncompleteReadError:
            self._connected = False
            raise ConnectionError("TCP connection closed by peer")
        except asyncio.TimeoutError:
            raise TimeoutError("TCP recv timeout")

        length = struct.unpack(">I", header)[0]
        if length == 0 or length > MAX_MESSAGE_SIZE:
            raise ValueError(f"Invalid frame length: {length}")

        try:
            data = await asyncio.wait_for(
                self._reader.readexactly(length), timeout=30.0
            )
        except asyncio.IncompleteReadError:
            self._connected = False
            raise ConnectionError("TCP connection closed mid-frame")

        self._stats.bytes_recv += len(data)
        self._stats.packets_recv += 1
        return data

    async def close(self) -> None:
        if not self._connected:
            return
        self._connected = False
        try:
            self._writer.close()
            await self._writer.wait_closed()
        except Exception:
            pass

    @property
    def peer_addr(self) -> tuple[str, int]:
        return self._peer_addr

    @property
    def congestion(self) -> CongestionController:
        return self._congestion


ConnectionCallback = Callable[[TCPConnection], Awaitable[None]]


class TCPTransport:
    def __init__(self) -> None:
        self._server: asyncio.Server | None = None

    async def start_server(
        self,
        host: str,
        port: int,
        on_connection: ConnectionCallback,
    ) -> asyncio.Server:
        async def handle_client(
            reader: asyncio.StreamReader, writer: asyncio.StreamWriter
        ) -> None:
            addr = writer.get_extra_info("peername", ("unknown", 0))
            conn = TCPConnection(reader, writer, tuple(addr))
            logger.info("tcp.connection.accepted", peer=addr)
            try:
                await on_connection(conn)
            except Exception as exc:
                logger.warning("tcp.connection.error", peer=addr, error=str(exc))
            finally:
                await conn.close()

        self._server = await asyncio.start_server(handle_client, host, port)
        logger.info("tcp.server.started", host=host, port=port)
        return self._server

    async def connect(self, host: str, port: int) -> TCPConnection:
        reader, writer = await asyncio.open_connection(host, port)
        addr = writer.get_extra_info("peername", (host, port))
        conn = TCPConnection(reader, writer, tuple(addr))
        logger.info("tcp.connection.established", host=host, port=port)
        return conn

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
