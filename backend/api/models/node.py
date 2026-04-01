from pydantic import BaseModel
from typing import Optional


class NodeInfoResponse(BaseModel):
    node_id: str
    role: str
    host: str
    tcp_port: int
    udp_port: int
    quic_port: int
    state: str
    current_transport: str
    last_seen: float
    peer_ids: list[str]


class FailureInjectionRequest(BaseModel):
    failure_mode: str
    duration_s: float = 10.0
    intensity: float = 1.0


class NodeStateHistoryItem(BaseModel):
    time: str
    state: str
    transport: Optional[str]
