import { useSelector } from 'react-redux'
import { selectAllNodes } from '../../store/nodesSlice'
import { NodeCard } from './NodeCard'

export function TelemetryPanel() {
  const nodes = useSelector(selectAllNodes)

  return (
    <div style={styles.panel}>
      <div style={styles.title}>NODES</div>
      <div style={styles.grid}>
        {nodes.map(n => (
          <NodeCard key={n.node_id} nodeId={n.node_id} />
        ))}
        {nodes.length === 0 && (
          <div style={styles.empty}>Waiting for nodes...</div>
        )}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  panel: { height: '100%', display: 'flex', flexDirection: 'column' },
  title: { fontSize: 10, fontWeight: 700, letterSpacing: 2, color: '#475569', marginBottom: 8 },
  grid: { flex: 1, overflowY: 'auto', display: 'grid', gridTemplateColumns: '1fr', gap: 6 },
  empty: { color: '#334155', fontSize: 12, textAlign: 'center', paddingTop: 20 },
}
