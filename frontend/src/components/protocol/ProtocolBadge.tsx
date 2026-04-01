import { color } from '../../tokens'

const COLORS: Record<string, { bg: string; text: string }> = {
  tcp: { bg: color.transportBg.tcp, text: color.transportText.tcp },
  udp: { bg: color.transportBg.udp, text: color.transportText.udp },
  quic: { bg: color.transportBg.quic, text: color.transportText.quic },
}

interface Props {
  transport: string
}

export function ProtocolBadge({ transport }: Props) {
  const style = COLORS[transport] ?? { bg: '#1e2533', text: '#94a3b8' }
  return (
    <span
      style={{
        background: style.bg,
        color: style.text,
        fontSize: 9,
        fontWeight: 700,
        letterSpacing: 1,
        padding: '2px 6px',
        borderRadius: 4,
        textTransform: 'uppercase',
      }}
    >
      {transport}
    </span>
  )
}
