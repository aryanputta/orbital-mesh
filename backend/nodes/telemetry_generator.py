import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum


class FailureType(str, Enum):
    NORMAL = "normal"
    OVERHEATING = "overheating"
    POWER_FAULT = "power_fault"
    MECHANICAL_FAILURE = "mechanical_failure"
    NETWORK_DEGRADATION = "network_degradation"
    SENSOR_FAULT = "sensor_fault"


@dataclass
class TelemetryFrame:
    node_id: str
    timestamp: str
    sequence_number: int
    temperature_c: float
    voltage_v: float
    rpm: float
    latency_ms: float
    packet_loss_pct: float
    uptime_s: float
    injected_failure: FailureType = FailureType.NORMAL

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "timestamp": self.timestamp,
            "sequence_number": self.sequence_number,
            "temperature_c": round(self.temperature_c, 3),
            "voltage_v": round(self.voltage_v, 3),
            "rpm": round(self.rpm, 1),
            "latency_ms": round(self.latency_ms, 3),
            "packet_loss_pct": round(self.packet_loss_pct, 4),
            "uptime_s": round(self.uptime_s, 1),
            "injected_failure": self.injected_failure.value,
        }

    def to_features(self) -> list[float]:
        return [
            self.temperature_c,
            self.voltage_v,
            self.rpm,
            self.latency_ms,
            self.packet_loss_pct,
            self.uptime_s,
        ]


class TelemetryGenerator:
    BASE_TEMP = 25.0
    BASE_VOLTAGE = 12.0
    BASE_RPM = 2500.0
    BASE_LATENCY = 10.0

    def __init__(self, node_id: str, anomaly_rate: float = 0.02) -> None:
        self._node_id = node_id
        self._anomaly_rate = anomaly_rate
        self._sequence = 0
        self._start_time = time.monotonic()
        self._phase_offset = random.uniform(0, 2 * math.pi)
        self._voltage_drift = 0.0
        self._forced_failure: FailureType | None = None

    def force_failure(self, failure_type: FailureType | None) -> None:
        self._forced_failure = failure_type

    def generate(self, network_rtt_ms: float = 0.0, network_loss: float = 0.0) -> TelemetryFrame:
        self._sequence += 1
        uptime = time.monotonic() - self._start_time
        phase = uptime * 0.1 + self._phase_offset
        self._voltage_drift += random.gauss(0, 0.001)
        self._voltage_drift = max(-1.5, min(1.5, self._voltage_drift))

        failure = self._forced_failure or self._maybe_inject_failure()

        temp = self._generate_temp(phase, failure)
        voltage = self._generate_voltage(failure)
        rpm = self._generate_rpm(phase, failure)
        latency = self._generate_latency(network_rtt_ms, failure)
        loss = self._generate_loss(network_loss, failure)

        return TelemetryFrame(
            node_id=self._node_id,
            timestamp=_iso_now(),
            sequence_number=self._sequence,
            temperature_c=temp,
            voltage_v=voltage,
            rpm=rpm,
            latency_ms=latency,
            packet_loss_pct=loss,
            uptime_s=uptime,
            injected_failure=failure,
        )

    def _maybe_inject_failure(self) -> FailureType:
        if random.random() < self._anomaly_rate:
            return random.choice([
                FailureType.OVERHEATING,
                FailureType.POWER_FAULT,
                FailureType.MECHANICAL_FAILURE,
                FailureType.NETWORK_DEGRADATION,
                FailureType.SENSOR_FAULT,
            ])
        return FailureType.NORMAL

    def _generate_temp(self, phase: float, failure: FailureType) -> float:
        base = self.BASE_TEMP + 10.0 * math.sin(phase) + random.gauss(0, 0.5)
        if failure == FailureType.OVERHEATING:
            base += random.uniform(20, 50)
        elif failure == FailureType.SENSOR_FAULT:
            base += random.choice([-30, 30]) * random.random()
        return max(-40.0, min(200.0, base))

    def _generate_voltage(self, failure: FailureType) -> float:
        base = self.BASE_VOLTAGE + self._voltage_drift + random.gauss(0, 0.05)
        if failure == FailureType.POWER_FAULT:
            base *= random.uniform(0.6, 0.85)
        elif failure == FailureType.SENSOR_FAULT:
            base += random.gauss(0, 2.0)
        return max(0.0, min(24.0, base))

    def _generate_rpm(self, phase: float, failure: FailureType) -> float:
        base = self.BASE_RPM + 500.0 * math.cos(phase * 0.5) + random.gauss(0, 20)
        if failure == FailureType.MECHANICAL_FAILURE:
            base *= random.uniform(0.3, 0.7)
        elif failure == FailureType.OVERHEATING:
            base *= random.uniform(0.8, 0.95)
        return max(0.0, min(8000.0, base))

    def _generate_latency(self, network_rtt_ms: float, failure: FailureType) -> float:
        base = max(network_rtt_ms, self.BASE_LATENCY)
        jitter = abs(random.expovariate(1.0 / 5.0))
        if failure == FailureType.NETWORK_DEGRADATION:
            base *= random.uniform(3, 10)
        return max(0.1, base + jitter)

    def _generate_loss(self, network_loss: float, failure: FailureType) -> float:
        base = network_loss + max(0, random.gauss(0, 0.005))
        if failure == FailureType.NETWORK_DEGRADATION:
            base += random.uniform(0.05, 0.3)
        return max(0.0, min(1.0, base))


def _iso_now() -> str:
    import datetime
    return datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
