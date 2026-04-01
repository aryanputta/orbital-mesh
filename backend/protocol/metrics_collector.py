import time
from collections import deque
from dataclasses import dataclass, field

from network.base_transport import TransportStats, TransportType


@dataclass
class TransportSample:
    timestamp: float
    rtt_ms: float
    packet_loss_rate: float
    throughput_bps: float
    jitter_ms: float


class TransportMetricsWindow:
    def __init__(self, maxlen: int = 20) -> None:
        self._samples: deque[TransportSample] = deque(maxlen=maxlen)

    def record(self, stats: TransportStats) -> None:
        self._samples.append(
            TransportSample(
                timestamp=time.monotonic(),
                rtt_ms=stats.rtt_ms,
                packet_loss_rate=stats.packet_loss_rate,
                throughput_bps=stats.throughput_bps,
                jitter_ms=stats.jitter_ms,
            )
        )

    def avg_rtt(self) -> float:
        if not self._samples:
            return 0.0
        return sum(s.rtt_ms for s in self._samples) / len(self._samples)

    def avg_loss(self) -> float:
        if not self._samples:
            return 0.0
        return sum(s.packet_loss_rate for s in self._samples) / len(self._samples)

    def avg_throughput(self) -> float:
        if not self._samples:
            return 0.0
        return sum(s.throughput_bps for s in self._samples) / len(self._samples)

    def avg_jitter(self) -> float:
        if not self._samples:
            return 0.0
        return sum(s.jitter_ms for s in self._samples) / len(self._samples)

    def score(self) -> float:
        rtt = max(self.avg_rtt(), 0.001)
        loss = self.avg_loss()
        throughput = max(self.avg_throughput(), 1.0)
        return (1.0 / rtt) * (1.0 - loss) * throughput

    def sample_count(self) -> int:
        return len(self._samples)


class MetricsCollector:
    def __init__(self, window_size: int = 20) -> None:
        self._windows: dict[TransportType, TransportMetricsWindow] = {
            t: TransportMetricsWindow(window_size) for t in TransportType
        }

    def record(self, transport_type: TransportType, stats: TransportStats) -> None:
        self._windows[transport_type].record(stats)

    def avg_rtt(self, transport_type: TransportType) -> float:
        return self._windows[transport_type].avg_rtt()

    def avg_loss(self, transport_type: TransportType) -> float:
        return self._windows[transport_type].avg_loss()

    def avg_throughput(self, transport_type: TransportType) -> float:
        return self._windows[transport_type].avg_throughput()

    def score(self, transport_type: TransportType) -> float:
        return self._windows[transport_type].score()

    def best_transport(self) -> TransportType:
        return max(TransportType, key=lambda t: self._windows[t].score())

    def snapshot(self) -> dict:
        return {
            t.value: {
                "avg_rtt_ms": round(self._windows[t].avg_rtt(), 3),
                "avg_loss": round(self._windows[t].avg_loss(), 4),
                "avg_throughput_bps": round(self._windows[t].avg_throughput(), 2),
                "avg_jitter_ms": round(self._windows[t].avg_jitter(), 3),
                "score": round(self._windows[t].score(), 6),
                "samples": self._windows[t].sample_count(),
            }
            for t in TransportType
        }
