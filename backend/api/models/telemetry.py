from pydantic import BaseModel
from typing import Optional


class TelemetryFrameResponse(BaseModel):
    node_id: str
    timestamp: str
    sequence_number: int
    temperature_c: float
    voltage_v: float
    rpm: float
    latency_ms: float
    packet_loss_pct: float
    uptime_s: float
    injected_failure: str


class TelemetryAggregateResponse(BaseModel):
    node_id: str
    bucket: str
    temperature_avg: Optional[float]
    temperature_min: Optional[float]
    temperature_max: Optional[float]
    voltage_avg: Optional[float]
    latency_avg: Optional[float]
    packet_loss_avg: Optional[float]
