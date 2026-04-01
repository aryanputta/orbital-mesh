interface Props {
  score: number
}

export function ConfidenceBar({ score }: Props) {
  const clamped = Math.max(0, Math.min(1, score))
  const pct = (clamped * 100).toFixed(0)
  const hue = Math.round((1 - clamped) * 60)
  const color = `hsl(${hue}, 90%, 55%)`

  return (
    <div style={styles.wrapper}>
      <div style={{ ...styles.fill, width: `${pct}%`, background: color }} />
      <span style={styles.label}>{pct}%</span>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    position: 'relative',
    height: 6,
    background: '#1e2533',
    borderRadius: 3,
    overflow: 'visible',
    display: 'flex',
    alignItems: 'center',
  },
  fill: {
    height: '100%',
    borderRadius: 3,
    transition: 'width 0.3s',
  },
  label: {
    position: 'absolute',
    right: 0,
    top: -14,
    fontSize: 9,
    color: '#94a3b8',
  },
}
