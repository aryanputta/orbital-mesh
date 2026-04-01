import { useState } from 'react'
import { useSelector } from 'react-redux'
import { selectAllNodes } from '../../store/nodesSlice'
import { injectFailure, recoverNode } from '../../api/client'

const FAILURE_MODES = [
  'node_crash',
  'congestion_burst',
  'packet_drop_storm',
  'delayed_response',
  'link_partition',
]

export function ControlPanel() {
  const nodes = useSelector(selectAllNodes)
  const [selectedNode, setSelectedNode] = useState('')
  const [mode, setMode] = useState(FAILURE_MODES[0])
  const [duration, setDuration] = useState(10)
  const [intensity, setIntensity] = useState(1.0)
  const [status, setStatus] = useState<string | null>(null)

  const handleInject = async () => {
    if (!selectedNode) return
    try {
      await injectFailure(selectedNode, mode, duration, intensity)
      setStatus(`Injected ${mode} on ${selectedNode}`)
    } catch {
      setStatus('Injection failed')
    }
    setTimeout(() => setStatus(null), 3000)
  }

  const handleRecover = async () => {
    if (!selectedNode) return
    try {
      await recoverNode(selectedNode)
      setStatus(`Recovered ${selectedNode}`)
    } catch {
      setStatus('Recovery failed')
    }
    setTimeout(() => setStatus(null), 3000)
  }

  return (
    <div style={styles.panel}>
      <div style={styles.title}>FAILURE INJECTION</div>
      <div style={styles.form}>
        <label style={styles.label}>Node</label>
        <select style={styles.select} value={selectedNode} onChange={e => setSelectedNode(e.target.value)}>
          <option value="">Select node</option>
          {nodes.map(n => <option key={n.node_id} value={n.node_id}>{n.node_id}</option>)}
        </select>

        <label style={styles.label}>Failure Mode</label>
        <select style={styles.select} value={mode} onChange={e => setMode(e.target.value)}>
          {FAILURE_MODES.map(m => <option key={m} value={m}>{m.replace(/_/g, ' ')}</option>)}
        </select>

        <div style={styles.row}>
          <div style={{ flex: 1 }}>
            <label style={styles.label}>Duration (s)</label>
            <input
              type="number"
              style={styles.input}
              value={duration}
              min={1}
              max={300}
              onChange={e => setDuration(Number(e.target.value))}
            />
          </div>
          <div style={{ flex: 1 }}>
            <label style={styles.label}>Intensity</label>
            <input
              type="number"
              style={styles.input}
              value={intensity}
              min={0.1}
              max={1}
              step={0.1}
              onChange={e => setIntensity(Number(e.target.value))}
            />
          </div>
        </div>

        <div style={styles.btnRow}>
          <button style={styles.dangerBtn} onClick={handleInject} disabled={!selectedNode}>
            Inject
          </button>
          <button style={styles.safeBtn} onClick={handleRecover} disabled={!selectedNode}>
            Recover
          </button>
        </div>

        {status && <div style={styles.status}>{status}</div>}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  panel: { padding: '0' },
  title: { fontSize: 10, fontWeight: 700, letterSpacing: 2, color: '#475569', marginBottom: 12 },
  form: { display: 'flex', flexDirection: 'column', gap: 8 },
  label: { fontSize: 10, color: '#475569', letterSpacing: 1, display: 'block', marginBottom: 2 },
  select: { width: '100%', background: '#0f1117', border: '1px solid #1e2533', color: '#e2e8f0', padding: '6px 8px', borderRadius: 4, fontSize: 12 },
  input: { width: '100%', background: '#0f1117', border: '1px solid #1e2533', color: '#e2e8f0', padding: '6px 8px', borderRadius: 4, fontSize: 12 },
  row: { display: 'flex', gap: 8 },
  btnRow: { display: 'flex', gap: 8, marginTop: 4 },
  dangerBtn: { flex: 1, background: '#7f1d1d', color: '#fca5a5', border: 'none', padding: '8px', borderRadius: 6, fontSize: 12, cursor: 'pointer', fontWeight: 600 },
  safeBtn: { flex: 1, background: '#14532d', color: '#86efac', border: 'none', padding: '8px', borderRadius: 6, fontSize: 12, cursor: 'pointer', fontWeight: 600 },
  status: { fontSize: 11, color: '#6366f1', textAlign: 'center', padding: '4px 0' },
}
