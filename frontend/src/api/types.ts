export type NodeRole = 'coordinator' | 'relay' | 'leaf'
export type NodeState = 'online' | 'degraded' | 'offline' | 'recovering'
export type TransportType = 'tcp' | 'udp' | 'quic'
export type FailureClass =
  | 'normal'
  | 'overheating'
  | 'power_fault'
  | 'mechanical_failure'
  | 'network_degradation'
  | 'sensor_fault'

export interface NodeInfo {
  node_id: string
  role: NodeRole
  host: string
  tcp_port: number
  udp_port: number
  quic_port: number
  state: NodeState
  current_transport: TransportType
  last_seen: number
  peer_ids: string[]
}

export interface TelemetryFrame {
  node_id: string
  timestamp: string
  sequence_number: number
  temperature_c: number
  voltage_v: number
  rpm: number
  latency_ms: number
  packet_loss_pct: number
  uptime_s: number
  injected_failure: FailureClass
}

export interface EdgeInfo {
  source: string
  target: string
  transport: TransportType
  rtt_ms: number
  loss_rate: number
  throughput_bps: number
}

export interface TopologySnapshot {
  nodes: Array<{ id: string; role: string; state: string; transport?: string }>
  edges: EdgeInfo[]
}

export interface AnomalyEvent {
  id: number
  time: string
  node_id: string
  anomaly_score: number
  failure_class: FailureClass
  confidence: number
}

export interface ProtocolSwitchEvent {
  id: number
  time: string
  node_id: string
  from_transport: TransportType
  to_transport: TransportType
  reason: string
  rtt_before: number
  rtt_after: number
}

export interface FailoverEvent {
  id: number
  time: string
  failed_node: string
  rerouted_via: string[]
  duration_ms: number
}

export interface WebSocketMessage<T = unknown> {
  topic: string
  data: T
  timestamp: string
}
