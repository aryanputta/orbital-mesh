import { NavLink } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: '⬡' },
  { to: '/protocols', label: 'Protocol Analysis', icon: '⇄' },
]

export function Sidebar() {
  return (
    <nav style={styles.nav}>
      <div style={styles.logo}>
        <span style={styles.logoIcon}>◉</span>
        <span style={styles.logoText}>ORBITAL MESH</span>
      </div>
      <div style={styles.links}>
        {NAV_ITEMS.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            style={({ isActive }) => ({
              ...styles.link,
              background: isActive ? '#1e2533' : 'transparent',
              color: isActive ? '#818cf8' : '#94a3b8',
            })}
          >
            <span style={styles.icon}>{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}

const styles: Record<string, React.CSSProperties> = {
  nav: {
    width: 200,
    background: '#0d111c',
    borderRight: '1px solid #1e2533',
    display: 'flex',
    flexDirection: 'column',
    flexShrink: 0,
  },
  logo: {
    padding: '20px 16px',
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    borderBottom: '1px solid #1e2533',
  },
  logoIcon: { fontSize: 20, color: '#818cf8' },
  logoText: { fontSize: 11, fontWeight: 700, letterSpacing: 2, color: '#e2e8f0' },
  links: { padding: '8px 0' },
  link: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '10px 16px',
    textDecoration: 'none',
    fontSize: 13,
    borderRadius: 6,
    margin: '2px 8px',
    transition: 'all 0.15s',
  },
  icon: { fontSize: 14, width: 20, textAlign: 'center' },
}
