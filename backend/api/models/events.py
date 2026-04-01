from pydantic import BaseModel
from typing import Any, Optional


class AnomalyEventResponse(BaseModel):
    id: Optional[int]
    time: str
    node_id: str
    anomaly_score: float
    failure_class: str
    confidence: float


class ProtocolSwitchResponse(BaseModel):
    id: Optional[int]
    time: str
    node_id: str
    from_transport: str
    to_transport: str
    reason: Optional[str]
    rtt_before: Optional[float]
    rtt_after: Optional[float]


class FailoverEventResponse(BaseModel):
    id: Optional[int]
    time: str
    failed_node: str
    rerouted_via: list[str]
    duration_ms: Optional[float]


class WebSocketMessage(BaseModel):
    topic: str
    data: Any
    timestamp: str
