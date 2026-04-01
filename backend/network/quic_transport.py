import asyncio
import ssl
import time
from typing import cast

from aioquic.asyncio import connect as quic_connect, serve as quic_serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent, StreamDataReceived, ConnectionTerminated

from network.base_transport import BaseTransport, TransportType
from core.logging import get_logger

logger = get_logger(__name__)


class OrbitalQuicProtocol(QuicConnectionProtocol):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._recv_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=10000)
        self._send_stream_id: int | None = None
        self._bytes_sent = 0
        self._bytes_recv = 0

    def quic_event_received(self, event: QuicEvent) -> None:
        if isinstance(event, StreamDataReceived):
            if event.data:
                try:
                    self._recv_queue.put_nowait(event.data)
                except asyncio.QueueFull:
                    pass
                self._bytes_recv += len(event.data)
        elif isinstance(event, ConnectionTerminated):
            logger.info("quic.connection.terminated", error=event.error_code)

    async def send_data(self, data: bytes) -> int:
        if self._send_stream_id is None:
            self._send_stream_id = self._quic.get_next_available_stream_id(is_unidirectional=False)
        self._quic.send_stream_data(self._send_stream_id, data, end_stream=False)
        self.transmit()
        self._bytes_sent += len(data)
        return len(data)

    async def recv_data(self) -> bytes:
        return await self._recv_queue.get()

    @property
    def bytes_sent(self) -> int:
        return self._bytes_sent

    @property
    def bytes_recv(self) -> int:
        return self._bytes_recv


class QUICTransport(BaseTransport):
    def __init__(self, cert_path: str, key_path: str, is_server: bool = False) -> None:
        super().__init__(TransportType.QUIC)
        self._cert_path = cert_path
        self._key_path = key_path
        self._is_server = is_server
        self._protocol: OrbitalQuicProtocol | None = None
        self._server = None
        self._connect_start: float = 0.0

    def _make_configuration(self) -> QuicConfiguration:
        config = QuicConfiguration(is_client=not self._is_server)
        config.verify_mode = ssl.CERT_NONE
        if self._is_server:
            config.load_cert_chain(self._cert_path, self._key_path)
        else:
            with open(self._cert_path, "rb") as f:
                config.load_verify_locations(cadata=f.read())
        return config

    async def start_server(self, host: str, port: int) -> None:
        config = self._make_configuration()

        async def protocol_factory(*args, **kwargs) -> OrbitalQuicProtocol:
            return OrbitalQuicProtocol(*args, **kwargs)

        self._server = await quic_serve(
            host,
            port,
            configuration=config,
            create_protocol=protocol_factory,
        )
        self._connected = True
        logger.info("quic.server.started", host=host, port=port)

    async def connect(self, host: str, port: int) -> None:
        config = self._make_configuration()
        self._connect_start = time.monotonic()
        async with quic_connect(
            host,
            port,
            configuration=config,
            create_protocol=OrbitalQuicProtocol,
        ) as protocol:
            self._protocol = cast(OrbitalQuicProtocol, protocol)
            self._connected = True
            rtt_ms = (time.monotonic() - self._connect_start) * 1000
            self._stats.rtt_ms = rtt_ms
            logger.info("quic.connected", host=host, port=port, rtt_ms=round(rtt_ms, 2))
            await protocol.wait_closed()

    async def send(self, data: bytes) -> int:
        if not self._protocol or not self._connected:
            raise ConnectionError("QUIC not connected")
        sent = await self._protocol.send_data(data)
        self._stats.bytes_sent += sent
        self._stats.packets_sent += 1
        return sent

    async def recv(self) -> bytes:
        if not self._protocol or not self._connected:
            raise ConnectionError("QUIC not connected")
        data = await self._protocol.recv_data()
        self._stats.bytes_recv += len(data)
        self._stats.packets_recv += 1
        return data

    async def close(self) -> None:
        self._connected = False
        if self._protocol:
            self._protocol.close()
            self._protocol = None
        if self._server:
            self._server.close()
            self._server = None
