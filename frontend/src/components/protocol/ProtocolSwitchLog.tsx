import { useEffect, useState } from 'react'
import { fetchRerouteHistory } from '../../api/client'
import { ProtocolBadge } from './ProtocolBadge'

interface SwitchRecord {
  node_id?: string
  from_transport?: string
  to_transport?: string
  reason?: string
  time?: string
  rtt_before?: number
  rtt_after?: number
}

export function ProtocolSwitchLog() {
  const [records, setRecords] = useState<SwitchRecord[]>([])

  useEffect(() => {
    fetchRerouteHistory()
      .then(data => setRecords(data as SwitchRecord[]))
      .catch(() => {})
    const id = setInterval(() => {
      fetchRerouteHistory()
        .then(data => setRecords(data as SwitchRecord[]))
        .catch(() => {})
    }, 5000)
    return () => clearInterval(id)
  }, [])

  return (
    <div style={styles.container}>
      <div style={styles.title}>PROTOCOL SWITCHES</div>
      <div style={styles.list}>
        {records.length === 0 && <div style={styles.empty}>No switches recorded</div>}
        {records.map((r, i) => (
          <div key={i} style={styles.row}>
            <span style={styles.nodeId}>{r.node_id ?? '—'}</span>
            <ProtocolBadge transport={r.from_transport ?? 'tcp'} />
            <span style={styles.arrow}>→</span>
            <ProtocolBadge transport={r.to_transport ?? 'tcp'} />
            <span style={styles.reason}>{r.reason ?? ''}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: { height: '100%', display: 'flex', flexDirection: 'column' },
  title: { fontSize: 10, fontWeight: 700, letterSpacing: 2, color: '#475569', marginBottom: 8 },
  list: { flex: 1, overflowY: 'auto' },
  empty: { color: '#334155', fontSize: 12 },
  row: { display: 'flex', alignItems: 'center', gap: 6, padding: '4px 0', borderBottom: '1px solid #0f1117', fontSize: 11 },
  nodeId: { color: '#94a3b8', width: 70, flexShrink: 0, fontSize: 10 },
  arrow: { color: '#475569' },
  reason: { color: '#475569', fontSize: 9, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
}
