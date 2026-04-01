import { useDispatch } from 'react-redux'
import { selectedNodeChanged } from '../../store/nodesSlice'
import { ConfidenceBar } from './ConfidenceBar'
import { color, space, font, radius } from '../../tokens'
import type { AnomalyEvent } from '../../api/types'
import type { AppDispatch } from '../../store'

const CLASS_LABELS: Record<string, string> = {
  normal: 'Normal',
  overheating: 'Overheating',
  power_fault: 'Power Fault',
  mechanical_failure: 'Mechanical Failure',
  network_degradation: 'Network Degradation',
  sensor_fault: 'Sensor Fault',
}

interface Props {
  event: AnomalyEvent
}

export function AnomalyCard({ event }: Props) {
  const dispatch = useDispatch<AppDispatch>()
  const label = CLASS_LABELS[event.failure_class] ?? event.failure_class.replace(/_/g, ' ')
  const time = new Date(event.time).toLocaleTimeString()

  return (
    <article
      style={styles.card}
      aria-label={`Anomaly: ${label} on ${event.node_id} at ${time}`}
    >
      <div style={styles.header}>
        <span style={styles.class}>{label}</span>
        <time style={styles.time} dateTime={event.time}>{time}</time>
      </div>
      <div style={styles.nodeRow}>
        <span style={styles.nodeLabel}>NODE</span>
        <button
          style={styles.nodeBtn}
          onClick={() => dispatch(selectedNodeChanged(event.node_id))}
          aria-label={`View node ${event.node_id}`}
        >
          {event.node_id}
        </button>
      </div>
      <div style={styles.barRow}>
        <span style={styles.barLabel}>Score</span>
        <div style={{ flex: 1, marginTop: space[2] }}>
          <ConfidenceBar score={event.anomaly_score} />
        </div>
      </div>
    </article>
  )
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: color.bg.elevated,
    border: `1px solid ${color.border.subtle}`,
    borderLeft: `3px solid ${color.anomaly.border}`,
    borderRadius: radius.md,
    padding: `${space[2]} ${space[3]}`,
    marginBottom: space[1],
  },
  header: { display: 'flex', alignItems: 'center', gap: space[1], marginBottom: space[1] },
  class: { fontSize: font.size.base, fontWeight: font.weight.semibold, color: color.anomaly.text, flex: 1 },
  time: { fontSize: font.size.xs, color: color.text.muted },
  nodeRow: { display: 'flex', alignItems: 'center', gap: space[1], marginBottom: space[1] },
  nodeLabel: { fontSize: font.size['2xs'], color: color.text.muted, letterSpacing: 1 },
  nodeBtn: {
    background: 'none',
    border: 'none',
    color: color.accent.primary,
    fontSize: font.size.sm,
    cursor: 'pointer',
    padding: 0,
    textDecoration: 'underline',
    minHeight: '44px',
    minWidth: '44px',
    display: 'inline-flex',
    alignItems: 'center',
  },
  barRow: { display: 'flex', alignItems: 'flex-start', gap: space[2] },
  barLabel: { fontSize: font.size['2xs'], color: color.text.muted, letterSpacing: 1, paddingTop: 2, whiteSpace: 'nowrap' },
}
