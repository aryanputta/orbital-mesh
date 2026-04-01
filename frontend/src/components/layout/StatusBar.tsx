import { useSelector } from 'react-redux'
import { selectAllNodes } from '../../store/nodesSlice'
import { selectUnreadCount } from '../../store/anomalySlice'
import { color, space, font } from '../../tokens'

interface Props {
  connected: boolean
}

export function StatusBar({ connected }: Props) {
  const nodes = useSelector(selectAllNodes)
  const unread = useSelector(selectUnreadCount)
  const online = nodes.filter(n => n.state === 'online').length
  const offline = nodes.filter(n => n.state === 'offline').length
  const degraded = nodes.filter(n => n.state === 'degraded').length

  return (
    <div style={styles.bar} role="status" aria-live="polite">
      <span
        style={{ ...styles.dot, background: connected ? color.node.online : color.node.offline }}
        aria-hidden="true"
      />
      <span style={styles.label}>{connected ? 'Live' : 'Disconnected'}</span>
      <span style={styles.sep} aria-hidden="true">|</span>
      <span style={styles.stat}>
        <span style={{ color: color.node.online }} aria-hidden="true">●</span>
        {' '}{online} online
      </span>
      <span style={styles.stat}>
        <span style={{ color: color.node.degraded }} aria-hidden="true">●</span>
        {' '}{degraded} degraded
      </span>
      <span style={styles.stat}>
        <span style={{ color: color.node.offline }} aria-hidden="true">●</span>
        {' '}{offline} offline
      </span>
      {unread > 0 && (
        <>
          <span style={styles.sep} aria-hidden="true">|</span>
          <span style={{ ...styles.stat, color: color.node.degraded }} aria-label={`${unread} unread alerts`}>
            ⚠ {unread} alerts
          </span>
        </>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: 'flex',
    alignItems: 'center',
    gap: space[2],
    padding: `6px ${space[4]}`,
    background: color.bg.elevated,
    borderTop: `1px solid ${color.border.subtle}`,
    fontSize: font.size.base,
    color: color.text.secondary,
    flexWrap: 'wrap',
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    display: 'inline-block',
    flexShrink: 0,
  },
  label: { color: color.text.primary, fontWeight: font.weight.medium },
  sep: { color: color.text.disabled, margin: `0 ${space[1]}` },
  stat: { color: color.text.secondary },
}
