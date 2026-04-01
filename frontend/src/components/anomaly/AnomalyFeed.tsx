import { useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useDispatch } from 'react-redux'
import { useAnomalyStream } from '../../hooks/useAnomalyStream'
import { clearUnread } from '../../store/anomalySlice'
import { AnomalyCard } from './AnomalyCard'
import type { AppDispatch } from '../../store'

export function AnomalyFeed() {
  const { events, unreadCount } = useAnomalyStream()
  const dispatch = useDispatch<AppDispatch>()
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: events.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 90,
    overscan: 5,
  })

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>ANOMALY FEED</span>
        {unreadCount > 0 && (
          <button style={styles.clearBtn} onClick={() => dispatch(clearUnread())}>
            {unreadCount} new — clear
          </button>
        )}
      </div>
      <div ref={parentRef} style={styles.scroll}>
        <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
          {virtualizer.getVirtualItems().map(item => (
            <div
              key={item.index}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${item.start}px)`,
              }}
            >
              <AnomalyCard event={events[item.index]} />
            </div>
          ))}
        </div>
        {events.length === 0 && <div style={styles.empty}>No anomalies detected</div>}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: { height: '100%', display: 'flex', flexDirection: 'column' },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 },
  title: { fontSize: 10, fontWeight: 700, letterSpacing: 2, color: '#475569' },
  clearBtn: {
    background: 'none',
    border: 'none',
    color: '#f59e0b',
    fontSize: 10,
    cursor: 'pointer',
    padding: 0,
  },
  scroll: { flex: 1, overflowY: 'auto' },
  empty: { color: '#334155', fontSize: 12, textAlign: 'center', paddingTop: 20 },
}
