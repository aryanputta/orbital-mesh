import { useEffect, useState } from 'react'
import { fetchFailoverHistory } from '../../api/client'
import type { FailoverEvent } from '../../api/types'

export function FailoverTimeline() {
  const [events, setEvents] = useState<FailoverEvent[]>([])

  useEffect(() => {
    const load = () => {
      fetchFailoverHistory()
        .then(data => setEvents(data))
        .catch(() => {})
    }
    load()
    const id = setInterval(load, 5000)
    return () => clearInterval(id)
  }, [])

  return (
    <div style={styles.container}>
      <div style={styles.title}>FAILOVER TIMELINE</div>
      {events.length === 0 ? (
        <div style={styles.empty}>No failover events</div>
      ) : (
        <div style={styles.list}>
          {events.map((e, i) => (
            <div key={i} style={styles.event}>
              <div style={styles.dot} />
              <div style={styles.content}>
                <div style={styles.eventHeader}>
                  <span style={styles.node}>{e.failed_node}</span>
                  <span style={styles.time}>{new Date(e.time).toLocaleTimeString()}</span>
                </div>
                {e.rerouted_via?.length > 0 && (
                  <div style={styles.via}>via {e.rerouted_via.join(' → ')}</div>
                )}
                {e.duration_ms != null && (
                  <div style={styles.duration}>{e.duration_ms.toFixed(0)}ms recovery</div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: { height: '100%', display: 'flex', flexDirection: 'column' },
  title: { fontSize: 10, fontWeight: 700, letterSpacing: 2, color: '#475569', marginBottom: 8 },
  empty: { color: '#334155', fontSize: 12 },
  list: { flex: 1, overflowY: 'auto' },
  event: { display: 'flex', gap: 10, marginBottom: 12, position: 'relative' },
  dot: { width: 8, height: 8, borderRadius: '50%', background: '#ef4444', flexShrink: 0, marginTop: 3 },
  content: { flex: 1 },
  eventHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  node: { fontSize: 12, fontWeight: 600, color: '#fca5a5' },
  time: { fontSize: 10, color: '#475569' },
  via: { fontSize: 10, color: '#94a3b8', marginTop: 2 },
  duration: { fontSize: 10, color: '#22c55e', marginTop: 2 },
}
