import { useSelector, useDispatch } from 'react-redux'
import { selectNodeById } from '../../store/nodesSlice'
import { selectLatestFrame } from '../../store/telemetrySlice'
import { selectedNodeChanged } from '../../store/nodesSlice'
import { ProtocolBadge } from '../protocol/ProtocolBadge'
import { color, space, font, radius } from '../../tokens'
import type { RootState } from '../../store'
import type { AppDispatch } from '../../store'

interface Props {
  nodeId: string
}

export function NodeCard({ nodeId }: Props) {
  const node = useSelector((s: RootState) => selectNodeById(s, nodeId))
  const latest = useSelector((s: RootState) => selectLatestFrame(nodeId)(s))
  const dispatch = useDispatch<AppDispatch>()

  if (!node) return null

  const stateColor = color.node[node.state as keyof typeof color.node] ?? color.text.muted

  return (
    <div
      style={styles.card}
      onClick={() => dispatch(selectedNodeChanged(nodeId))}
      role="button"
      tabIndex={0}
      aria-label={`Node ${nodeId}, state: ${node.state}`}
      onKeyDown={e => e.key === 'Enter' && dispatch(selectedNodeChanged(nodeId))}
    >
      <div style={styles.header}>
        <span style={{ ...styles.dot, background: stateColor }} aria-hidden="true" />
        <span style={styles.id}>{nodeId}</span>
        <span style={styles.role} aria-label={`Role: ${node.role}`}>{node.role}</span>
        <ProtocolBadge transport={node.current_transport} />
      </div>
      {latest && (
        <div style={styles.metrics}>
          <Metric label="TEMP" value={`${latest.temperature_c.toFixed(1)}°C`} />
          <Metric label="VOLT" value={`${latest.voltage_v.toFixed(2)}V`} />
          <Metric label="RTT" value={`${latest.latency_ms.toFixed(1)}ms`} />
          <Metric label="LOSS" value={`${(latest.packet_loss_pct * 100).toFixed(1)}%`} />
        </div>
      )}
    </div>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: font.size['2xs'], color: color.text.muted, letterSpacing: 1 }}>{label}</div>
      <div style={{ fontSize: font.size.base, color: color.text.primary, fontVariantNumeric: 'tabular-nums' }}>{value}</div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: color.bg.elevated,
    border: `1px solid ${color.border.subtle}`,
    borderRadius: radius.lg,
    padding: `${space[2]} ${space[3]}`,
    cursor: 'pointer',
    transition: 'border-color 0.15s ease-out',
    outline: 'none',
  },
  header: { display: 'flex', alignItems: 'center', gap: space[1], marginBottom: space[2] },
  dot: { width: 8, height: 8, borderRadius: '50%', flexShrink: 0 },
  id: { fontSize: font.size.base, fontWeight: font.weight.semibold, color: color.text.primary, flex: 1 },
  role: { fontSize: font.size['2xs'], color: color.text.muted, textTransform: 'uppercase', letterSpacing: 1 },
  metrics: { display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: space[1] },
}
