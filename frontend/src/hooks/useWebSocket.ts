import { useEffect, useRef, useState } from 'react'
import { useDispatch } from 'react-redux'
import { OrbitalWebSocket } from '../api/websocket'
import { nodeStateChanged, nodeUpdated } from '../store/nodesSlice'
import { telemetryReceived } from '../store/telemetrySlice'
import { anomalyReceived } from '../store/anomalySlice'
import { topologyUpdated } from '../store/topologySlice'
import type { NodeInfo, TelemetryFrame, AnomalyEvent, TopologySnapshot, WebSocketMessage } from '../api/types'
import type { AppDispatch } from '../store'

const WS_URL = import.meta.env.VITE_WS_URL ?? `ws://${window.location.host}/ws`

export function useWebSocket() {
  const dispatch = useDispatch<AppDispatch>()
  const wsRef = useRef<OrbitalWebSocket | null>(null)
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const ws = new OrbitalWebSocket(WS_URL)

    const unsubs = [
      ws.subscribe<TelemetryFrame>('telemetry.received', msg => {
        dispatch(telemetryReceived(msg.data))
      }),
      ws.subscribe<AnomalyEvent>('anomaly.detected', msg => {
        dispatch(anomalyReceived(msg.data))
      }),
      ws.subscribe<{ node_id: string; state: NodeInfo['state']; transport?: string }>(
        'node.failed',
        msg => {
          dispatch(nodeStateChanged({ node_id: msg.data.node_id, state: 'offline' }))
        },
      ),
      ws.subscribe<{ node_id: string; state: NodeInfo['state'] }>(
        'node.recovered',
        msg => {
          dispatch(nodeStateChanged({ node_id: msg.data.node_id, state: 'online' }))
        },
      ),
      ws.subscribe<{ node_id: string; state: string; transport: string }>(
        'node.heartbeat',
        msg => {
          dispatch(
            nodeStateChanged({
              node_id: msg.data.node_id,
              state: msg.data.state as NodeInfo['state'],
              transport: msg.data.transport,
            }),
          )
        },
      ),
      ws.subscribe<{ node_id: string; to: string }>(
        'protocol.switched',
        msg => {
          dispatch(nodeStateChanged({ node_id: msg.data.node_id, state: 'online', transport: msg.data.to }))
        },
      ),
    ]

    ws.connect()
    wsRef.current = ws

    const checkInterval = setInterval(() => {
      setConnected(ws.connected)
    }, 1000)

    return () => {
      clearInterval(checkInterval)
      unsubs.forEach(u => u())
      ws.disconnect()
    }
  }, [dispatch])

  return { connected }
}
