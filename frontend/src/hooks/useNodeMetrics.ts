import { useSelector } from 'react-redux'
import { selectFramesForNode, selectLatestFrame } from '../store/telemetrySlice'
import { selectNodeById } from '../store/nodesSlice'
import type { RootState } from '../store'

export function useNodeMetrics(nodeId: string) {
  const frames = useSelector(selectFramesForNode(nodeId))
  const latest = useSelector(selectLatestFrame(nodeId))
  const node = useSelector((s: RootState) => selectNodeById(s, nodeId))

  const avgLatency =
    frames.length > 0
      ? frames.reduce((acc, f) => acc + f.latency_ms, 0) / frames.length
      : 0

  const avgLoss =
    frames.length > 0
      ? frames.reduce((acc, f) => acc + f.packet_loss_pct, 0) / frames.length
      : 0

  return { frames, latest, node, avgLatency, avgLoss }
}
