import math
from typing import TYPE_CHECKING

import torch
from torch import Tensor

if TYPE_CHECKING:
    from nodes.telemetry_generator import TelemetryFrame

FEATURE_DIM = 6


class WelfordStats:
    def __init__(self) -> None:
        self._count = 0
        self._mean = 0.0
        self._m2 = 0.0

    def update(self, value: float) -> None:
        self._count += 1
        delta = value - self._mean
        self._mean += delta / self._count
        delta2 = value - self._mean
        self._m2 += delta * delta2

    @property
    def mean(self) -> float:
        return self._mean

    @property
    def std(self) -> float:
        if self._count < 2:
            return 1.0
        variance = self._m2 / (self._count - 1)
        return math.sqrt(max(variance, 1e-8))

    @property
    def count(self) -> int:
        return self._count


class FeatureExtractor:
    FEATURE_NAMES = ["temperature_c", "voltage_v", "rpm", "latency_ms", "packet_loss_pct", "uptime_s"]

    def __init__(self) -> None:
        self._stats = {name: WelfordStats() for name in self.FEATURE_NAMES}

    def update_stats(self, frame: "TelemetryFrame") -> None:
        self._stats["temperature_c"].update(frame.temperature_c)
        self._stats["voltage_v"].update(frame.voltage_v)
        self._stats["rpm"].update(frame.rpm)
        self._stats["latency_ms"].update(frame.latency_ms)
        self._stats["packet_loss_pct"].update(frame.packet_loss_pct)
        self._stats["uptime_s"].update(frame.uptime_s)

    def extract(self, frames: list["TelemetryFrame"]) -> Tensor:
        for frame in frames:
            self.update_stats(frame)

        seq = []
        for frame in frames:
            features = [
                self._normalize("temperature_c", frame.temperature_c),
                self._normalize("voltage_v", frame.voltage_v),
                self._normalize("rpm", frame.rpm),
                self._normalize("latency_ms", frame.latency_ms),
                self._normalize("packet_loss_pct", frame.packet_loss_pct),
                self._normalize("uptime_s", frame.uptime_s),
            ]
            seq.append(features)

        tensor = torch.tensor(seq, dtype=torch.float32)
        return tensor.unsqueeze(0)

    def extract_single(self, frame: "TelemetryFrame") -> Tensor:
        self.update_stats(frame)
        features = [
            self._normalize("temperature_c", frame.temperature_c),
            self._normalize("voltage_v", frame.voltage_v),
            self._normalize("rpm", frame.rpm),
            self._normalize("latency_ms", frame.latency_ms),
            self._normalize("packet_loss_pct", frame.packet_loss_pct),
            self._normalize("uptime_s", frame.uptime_s),
        ]
        return torch.tensor([features], dtype=torch.float32)

    def _normalize(self, name: str, value: float) -> float:
        stats = self._stats[name]
        if stats.count < 2:
            return value
        return (value - stats.mean) / stats.std

    def stats_snapshot(self) -> dict:
        return {
            name: {"mean": s.mean, "std": s.std, "count": s.count}
            for name, s in self._stats.items()
        }
