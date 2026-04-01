import { useSelector } from 'react-redux'
import { selectNodeById } from '../store/nodesSlice'
import { MetricChart } from '../components/telemetry/MetricChart'
import { ProtocolBadge } from '../components/protocol/ProtocolBadge'
import { ConfidenceBar } from '../components/anomaly/ConfidenceBar'
import { useAnomalyStream } from '../hooks/useAnomalyStream'
import { injectFailure, recoverNode } from '../api/client'
import type { RootState } from '../store'

interface Props {
  nodeId: string
  onClose: () => void
}

export function NodeDetailDrawer({ nodeId, onClose }: Props) {
  const node = useSelector((s: RootState) => selectNodeById(s, nodeId))
  const { events } = useAnomalyStream(nodeId)
  const latestAnomaly = events[0]

  if (!node) return null

  return (
    <div style={styles.overlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div style={styles.drawer}>
        <div style={styles.header}>
          <div>
            <div style={styles.title}>{nodeId}</div>
            <div style={styles.sub}>{node.role} · <ProtocolBadge transport={node.current_transport} /></div>
          </div>
          <button style={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        <div style={styles.section}>
          <div style={styles.sectionTitle}>TEMPERATURE</div>
          <MetricChart nodeId={nodeId} metric="temperature_c" color="#f97316" unit="°C" threshold={70} height={100} />
        </div>
        <div style={styles.section}>
          <div style={styles.sectionTitle}>VOLTAGE</div>
          <MetricChart nodeId={nodeId} metric="voltage_v" color="#22c55e" unit="V" height={100} />
        </div>
        <div style={styles.section}>
          <div style={styles.sectionTitle}>LATENCY</div>
          <MetricChart nodeId={nodeId} metric="latency_ms" color="#6366f1" unit="ms" threshold={200} height={100} />
        </div>
        <div style={styles.section}>
          <div style={styles.sectionTitle}>PACKET LOSS</div>
          <MetricChart nodeId={nodeId} metric="packet_loss_pct" color="#ef4444" unit="%" height={100} />
        </div>

        {latestAnomaly && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>LATEST ANOMALY</div>
            <div style={{ marginBottom: 6 }}>
              <span style={{ color: '#fbbf24', fontSize: 13 }}>
                {latestAnomaly.failure_class.replace(/_/g, ' ')}
              </span>
              <span style={{ color: '#475569', fontSize: 11, marginLeft: 8 }}>
                {new Date(latestAnomaly.time).toLocaleTimeString()}
              </span>
            </div>
            <ConfidenceBar score={latestAnomaly.anomaly_score} />
          </div>
        )}

        <div style={styles.section}>
          <div style={styles.sectionTitle}>ACTIONS</div>
          <div style={styles.btnRow}>
            {['congestion_burst', 'packet_drop_storm', 'delayed_response'].map(mode => (
              <button
                key={mode}
                style={styles.actionBtn}
                onClick={() => injectFailure(nodeId, mode)}
              >
                {mode.replace(/_/g, ' ')}
              </button>
            ))}
            <button
              style={{ ...styles.actionBtn, color: '#86efac', borderColor: '#166534' }}
              onClick={() => recoverNode(nodeId)}
            >
              recover
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(0,0,0,0.4)',
    zIndex: 50,
    display: 'flex',
    justifyContent: 'flex-end',
  },
  drawer: {
    width: 360,
    background: '#0d111c',
    borderLeft: '1px solid #1e2533',
    padding: '16px',
    overflowY: 'auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  title: { fontSize: 18, fontWeight: 700, color: '#e2e8f0' },
  sub: { fontSize: 12, color: '#475569', marginTop: 4, display: 'flex', alignItems: 'center', gap: 8 },
  closeBtn: {
    background: 'none',
    border: 'none',
    color: '#475569',
    fontSize: 18,
    cursor: 'pointer',
    padding: 4,
  },
  section: { marginBottom: 16 },
  sectionTitle: { fontSize: 9, fontWeight: 700, letterSpacing: 2, color: '#475569', marginBottom: 6 },
  btnRow: { display: 'flex', flexWrap: 'wrap', gap: 6 },
  actionBtn: {
    background: 'none',
    border: '1px solid #1e2533',
    color: '#fca5a5',
    padding: '4px 8px',
    borderRadius: 4,
    fontSize: 11,
    cursor: 'pointer',
    textTransform: 'capitalize',
  },
}
