import { useEffect, useState } from 'react'
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  CartesianGrid,
} from 'recharts'
import { fetchRerouteHistory } from '../api/client'

interface SwitchPoint {
  rtt_before: number
  loss_before: number
  transport: string
  node_id: string
  time: string
}

const COLORS: Record<string, string> = {
  tcp: '#3b82f6',
  udp: '#f97316',
  quic: '#a855f7',
}

export function ProtocolAnalysis() {
  const [data, setData] = useState<SwitchPoint[]>([])

  useEffect(() => {
    fetchRerouteHistory()
      .then(raw => setData(raw as SwitchPoint[]))
      .catch(() => {})
  }, [])

  const byTransport = Object.keys(COLORS).map(t => ({
    transport: t,
    color: COLORS[t],
    points: data.filter(d => d.transport === t || !d.transport),
  }))

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <h1 style={styles.title}>Protocol Analysis</h1>
        <p style={styles.sub}>RTT vs packet loss by transport protocol — each point is a switch decision</p>
      </div>

      <div style={styles.chart}>
        <ResponsiveContainer width="100%" height={400}>
          <ScatterChart margin={{ top: 16, right: 24, left: 0, bottom: 16 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e2533" />
            <XAxis
              dataKey="rtt_before"
              name="RTT before"
              unit="ms"
              tick={{ fontSize: 11, fill: '#475569' }}
              label={{ value: 'RTT (ms)', position: 'insideBottom', offset: -10, fill: '#475569', fontSize: 11 }}
            />
            <YAxis
              dataKey="loss_before"
              name="Loss before"
              unit="%"
              tick={{ fontSize: 11, fill: '#475569' }}
              label={{ value: 'Packet Loss (%)', angle: -90, position: 'insideLeft', fill: '#475569', fontSize: 11 }}
            />
            <Tooltip
              cursor={{ stroke: '#334155' }}
              contentStyle={{ background: '#0f1117', border: '1px solid #1e2533', fontSize: 11 }}
              labelStyle={{ color: '#94a3b8' }}
            />
            <Legend wrapperStyle={{ fontSize: 12, color: '#94a3b8' }} />
            {byTransport.map(({ transport, color, points }) => (
              <Scatter
                key={transport}
                name={transport.toUpperCase()}
                data={points}
                fill={color}
                fillOpacity={0.7}
              />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div style={styles.tableSection}>
        <div style={styles.tableTitle}>SWITCH LOG</div>
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                {['Time', 'Node', 'From', 'To', 'RTT Before', 'RTT After'].map(h => (
                  <th key={h} style={styles.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.length === 0 ? (
                <tr><td colSpan={6} style={styles.empty}>No switch data</td></tr>
              ) : (
                data.map((row: any, i) => (
                  <tr key={i} style={i % 2 === 0 ? styles.evenRow : {}}>
                    <td style={styles.td}>{row.time ? new Date(row.time).toLocaleTimeString() : '—'}</td>
                    <td style={styles.td}>{row.node_id ?? '—'}</td>
                    <td style={styles.td}>{row.from_transport ?? '—'}</td>
                    <td style={styles.td}>{row.to_transport ?? '—'}</td>
                    <td style={styles.td}>{row.rtt_before?.toFixed(1) ?? '—'}ms</td>
                    <td style={styles.td}>{row.rtt_after?.toFixed(1) ?? '—'}ms</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  page: { maxWidth: 1100, margin: '0 auto' },
  header: { marginBottom: 24 },
  title: { fontSize: 24, fontWeight: 700, color: '#e2e8f0', marginBottom: 4 },
  sub: { fontSize: 13, color: '#475569' },
  chart: { background: '#0d111c', border: '1px solid #1e2533', borderRadius: 10, padding: '16px', marginBottom: 20 },
  tableSection: {},
  tableTitle: { fontSize: 10, fontWeight: 700, letterSpacing: 2, color: '#475569', marginBottom: 8 },
  tableWrap: { overflowX: 'auto' },
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 12 },
  th: { padding: '8px 12px', textAlign: 'left', color: '#475569', fontSize: 10, letterSpacing: 1, borderBottom: '1px solid #1e2533', whiteSpace: 'nowrap' },
  td: { padding: '7px 12px', color: '#94a3b8', borderBottom: '1px solid #0f1117' },
  evenRow: { background: '#0d111c' },
  empty: { padding: 20, textAlign: 'center', color: '#334155' },
}
