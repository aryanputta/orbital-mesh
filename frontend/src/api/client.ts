import axios from 'axios'
import type {
  NodeInfo,
  TelemetryFrame,
  TopologySnapshot,
  AnomalyEvent,
  ProtocolSwitchEvent,
  FailoverEvent,
} from './types'

const http = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api/v1',
  timeout: 10_000,
})

export const fetchNodes = (): Promise<NodeInfo[]> =>
  http.get<NodeInfo[]>('/nodes/').then(r => r.data)

export const fetchNode = (nodeId: string): Promise<NodeInfo> =>
  http.get<NodeInfo>(`/nodes/${nodeId}`).then(r => r.data)

export const fetchTopology = (): Promise<TopologySnapshot> =>
  http.get<TopologySnapshot>('/topology/').then(r => r.data)

export const fetchTelemetry = (nodeId: string, limit = 100): Promise<TelemetryFrame[]> =>
  http.get<TelemetryFrame[]>(`/telemetry/${nodeId}`, { params: { limit } }).then(r => r.data)

export const fetchAnomalies = (
  nodeId?: string,
  failureClass?: string,
  limit = 50,
): Promise<AnomalyEvent[]> =>
  http
    .get<AnomalyEvent[]>('/anomalies/', {
      params: { node_id: nodeId, failure_class: failureClass, limit },
    })
    .then(r => r.data)

export const fetchAnomalySummary = (): Promise<Record<string, number>> =>
  http.get<Record<string, number>>('/anomalies/summary').then(r => r.data)

export const fetchFailoverHistory = (): Promise<FailoverEvent[]> =>
  http.get<FailoverEvent[]>('/control/failover-history').then(r => r.data)

export const fetchRerouteHistory = (): Promise<unknown[]> =>
  http.get<unknown[]>('/control/reroute-history').then(r => r.data)

export const injectFailure = (
  nodeId: string,
  failureMode: string,
  durationS = 10,
  intensity = 1.0,
): Promise<unknown> =>
  http
    .post(`/nodes/${nodeId}/inject-failure`, {
      failure_mode: failureMode,
      duration_s: durationS,
      intensity,
    })
    .then(r => r.data)

export const recoverNode = (nodeId: string): Promise<unknown> =>
  http.post(`/nodes/${nodeId}/recover`).then(r => r.data)

export const fetchSystemState = (): Promise<unknown> =>
  http.get('/control/system-state').then(r => r.data)
