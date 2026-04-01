import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { fetchNodes, fetchTopology, fetchAnomalies } from '../api/client'
import { allNodesLoaded, selectSelectedNodeId, selectedNodeChanged } from '../store/nodesSlice'
import { topologyUpdated } from '../store/topologySlice'
import { bulkAnomaliesLoaded } from '../store/anomalySlice'
import { TopologyGraph } from '../components/topology/TopologyGraph'
import { TelemetryPanel } from '../components/telemetry/TelemetryPanel'
import { AnomalyFeed } from '../components/anomaly/AnomalyFeed'
import { ControlPanel } from '../components/control/ControlPanel'
import { FailoverTimeline } from '../components/control/FailoverTimeline'
import { NodeDetailDrawer } from './NodeDetail'
import { ErrorBoundary } from '../components/shared/ErrorBoundary'
import { color, space, font, radius } from '../tokens'
import type { AppDispatch } from '../store'

export function Dashboard() {
  const dispatch = useDispatch<AppDispatch>()
  const selectedNodeId = useSelector(selectSelectedNodeId)

  useEffect(() => {
    const init = async () => {
      try {
        const [nodes, topology, anomalies] = await Promise.all([
          fetchNodes(),
          fetchTopology(),
          fetchAnomalies(undefined, undefined, 50),
        ])
        dispatch(allNodesLoaded(nodes))
        dispatch(topologyUpdated(topology))
        dispatch(bulkAnomaliesLoaded(anomalies))
      } catch {
        // API may not be ready yet; WS will hydrate state
      }
    }
    init()
  }, [dispatch])

  return (
    <div style={styles.grid}>
      <div style={styles.topologyArea}>
        <SectionCard title="NETWORK TOPOLOGY">
          <ErrorBoundary>
            <TopologyGraph />
          </ErrorBoundary>
        </SectionCard>
      </div>

      <div style={styles.telemetryArea}>
        <SectionCard title="LIVE TELEMETRY" scrollable>
          <TelemetryPanel />
        </SectionCard>
      </div>

      <div style={styles.anomalyArea}>
        <SectionCard title="ANOMALY FEED" scrollable>
          <AnomalyFeed />
        </SectionCard>
      </div>

      <div style={styles.controlArea}>
        <SectionCard title="CONTROL">
          <ControlPanel />
        </SectionCard>
      </div>

      <div style={styles.failoverArea}>
        <SectionCard title="FAILOVER HISTORY" scrollable>
          <FailoverTimeline />
        </SectionCard>
      </div>

      {selectedNodeId && (
        <NodeDetailDrawer
          nodeId={selectedNodeId}
          onClose={() => dispatch(selectedNodeChanged(null))}
        />
      )}
    </div>
  )
}

function SectionCard({
  title,
  children,
  scrollable,
}: {
  title: string
  children: React.ReactNode
  scrollable?: boolean
}) {
  return (
    <div style={{ ...styles.card, overflow: scrollable ? 'hidden' : 'visible' }}>
      <div style={styles.cardTitle}>{title}</div>
      <div style={{ flex: 1, overflow: scrollable ? 'auto' : 'visible' }}>{children}</div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  grid: {
    display: 'grid',
    gridTemplateColumns: 'clamp(300px, 1fr, 9999px) clamp(240px, 280px, 320px) clamp(240px, 280px, 320px)',
    gridTemplateRows: '1fr 260px',
    gridTemplateAreas: `
      "topology telemetry anomaly"
      "topology control failover"
    `,
    gap: space[3],
    height: '100%',
    minHeight: 0,
  },
  topologyArea: { gridArea: 'topology', minHeight: 0 },
  telemetryArea: { gridArea: 'telemetry', minHeight: 0 },
  anomalyArea: { gridArea: 'anomaly', minHeight: 0 },
  controlArea: { gridArea: 'control', minHeight: 0 },
  failoverArea: { gridArea: 'failover', minHeight: 0 },
  card: {
    background: color.bg.surface,
    border: `1px solid ${color.border.subtle}`,
    borderRadius: radius.xl,
    padding: `${space[3]} ${space[3]}`,
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
  },
  cardTitle: {
    fontSize: font.size.xs,
    fontWeight: font.weight.bold,
    letterSpacing: 2,
    color: color.text.disabled,
    marginBottom: space[2],
    flexShrink: 0,
  },
}
