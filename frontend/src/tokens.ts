export const space = {
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
} as const

export const radius = {
  sm: '4px',
  md: '6px',
  lg: '8px',
  xl: '10px',
  full: '9999px',
} as const

export const font = {
  size: {
    '2xs': '9px',
    xs: '10px',
    sm: '11px',
    base: '12px',
    md: '13px',
    lg: '14px',
    xl: '18px',
    '2xl': '24px',
  },
  weight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  leading: {
    tight: 1.2,
    normal: 1.5,
  },
} as const

export const color = {
  bg: {
    base: '#0a0e1a',
    surface: '#0d111c',
    elevated: '#0f1117',
    overlay: '#131929',
  },
  border: {
    subtle: '#1e2533',
    default: '#273044',
  },
  text: {
    primary: '#e2e8f0',
    secondary: '#94a3b8',
    muted: '#475569',
    disabled: '#334155',
  },
  node: {
    online: '#22c55e',
    degraded: '#f59e0b',
    offline: '#ef4444',
    recovering: '#6366f1',
  },
  transport: {
    tcp: '#3b82f6',
    udp: '#f97316',
    quic: '#a855f7',
  },
  transportBg: {
    tcp: '#1d3b70',
    udp: '#431407',
    quic: '#3b0764',
  },
  transportText: {
    tcp: '#60a5fa',
    udp: '#fb923c',
    quic: '#c084fc',
  },
  anomaly: {
    border: '#f59e0b',
    text: '#fbbf24',
    bg: '#451a03',
  },
  metric: {
    temperature: '#f97316',
    voltage: '#22c55e',
    latency: '#6366f1',
    loss: '#ef4444',
  },
  accent: {
    primary: '#818cf8',
    primaryBg: '#1e1b4b',
  },
  status: {
    success: '#22c55e',
    warning: '#f59e0b',
    danger: '#ef4444',
    info: '#3b82f6',
  },
} as const

export const shadow = {
  sm: '0 1px 2px rgba(0,0,0,0.4)',
  md: '0 4px 12px rgba(0,0,0,0.5)',
} as const

export const transition = {
  fast: 'all 0.1s ease-out',
  base: 'all 0.15s ease-out',
} as const
