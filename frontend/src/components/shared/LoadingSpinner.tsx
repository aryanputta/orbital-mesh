interface Props {
  size?: number
  color?: string
}

export function LoadingSpinner({ size = 24, color = '#6366f1' }: Props) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      style={{ animation: 'spin 1s linear infinite' }}
    >
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <circle cx="12" cy="12" r="10" stroke={color} strokeWidth="2" strokeDasharray="40 20" />
    </svg>
  )
}
