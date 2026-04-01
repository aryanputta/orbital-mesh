import { useSelector } from 'react-redux'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from 'recharts'
import { selectFramesForNode } from '../../store/telemetrySlice'
import type { TelemetryFrame } from '../../api/types'
import type { RootState } from '../../store'

interface Props {
  nodeId: string
  metric: keyof TelemetryFrame
  color?: string
  unit?: string
  threshold?: number
  height?: number
}

export function MetricChart({ nodeId, metric, color = '#6366f1', unit = '', threshold, height = 120 }: Props) {
  const frames = useSelector((s: RootState) => selectFramesForNode(nodeId)(s))
  const data = frames.slice(-60).map(f => ({
    value: f[metric] as number,
    time: new Date(f.timestamp).toLocaleTimeString(),
  }))

  if (data.length === 0) {
    return <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569', fontSize: 12 }}>No data</div>
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <XAxis dataKey="time" tick={{ fontSize: 9, fill: '#475569' }} interval="preserveStartEnd" />
        <YAxis tick={{ fontSize: 9, fill: '#475569' }} />
        <Tooltip
          contentStyle={{ background: '#0f1117', border: '1px solid #1e2533', fontSize: 11 }}
          formatter={(v: number) => [`${v.toFixed(2)}${unit}`, metric]}
          labelStyle={{ color: '#94a3b8' }}
        />
        {threshold && <ReferenceLine y={threshold} stroke="#ef4444" strokeDasharray="4 2" />}
        <Line
          type="monotone"
          dataKey="value"
          stroke={color}
          dot={false}
          strokeWidth={1.5}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
