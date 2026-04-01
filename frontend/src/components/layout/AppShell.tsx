import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { StatusBar } from './StatusBar'
import { useWebSocket } from '../../hooks/useWebSocket'

export function AppShell() {
  const { connected } = useWebSocket()
  return (
    <div style={styles.shell}>
      <Sidebar />
      <div style={styles.main}>
        <div style={styles.content}>
          <Outlet />
        </div>
        <StatusBar connected={connected} />
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  shell: { display: 'flex', height: '100vh', overflow: 'hidden' },
  main: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  content: { flex: 1, overflow: 'auto', padding: '16px' },
}
