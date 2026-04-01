from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import time


class TransportType(str, Enum):
    TCP = "tcp"
    UDP = "udp"
    QUIC = "quic"


@dataclass
class TransportStats:
    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0
    packets_dropped: int = 0
    rtt_ms: float = 0.0
    jitter_ms: float = 0.0
    packet_loss_rate: float = 0.0
    throughput_bps: float = 0.0
    last_updated: float = field(default_factory=time.monotonic)

    def update_throughput(self, window_s: float = 1.0) -> None:
        elapsed = time.monotonic() - self.last_updated
        if elapsed > 0:
            self.throughput_bps = (self.bytes_sent * 8) / max(elapsed, window_s)

    def to_dict(self) -> dict:
        return {
            "bytes_sent": self.bytes_sent,
            "bytes_recv": self.bytes_recv,
            "packets_sent": self.packets_sent,
            "packets_recv": self.packets_recv,
            "packets_dropped": self.packets_dropped,
            "rtt_ms": round(self.rtt_ms, 3),
            "jitter_ms": round(self.jitter_ms, 3),
            "packet_loss_rate": round(self.packet_loss_rate, 4),
            "throughput_bps": round(self.throughput_bps, 2),
        }


class BaseTransport(ABC):
    def __init__(self, transport_type: TransportType) -> None:
        self._transport_type = transport_type
        self._stats = TransportStats()
        self._connected = False

    @property
    def transport_type(self) -> TransportType:
        return self._transport_type

    @property
    def stats(self) -> TransportStats:
        return self._stats

    @property
    def connected(self) -> bool:
        return self._connected

    @abstractmethod
    async def connect(self, host: str, port: int) -> None:
        pass

    @abstractmethod
    async def send(self, data: bytes) -> int:
        pass

    @abstractmethod
    async def recv(self) -> bytes:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass
