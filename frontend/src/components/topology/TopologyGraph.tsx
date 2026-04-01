import { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import { useDispatch } from 'react-redux'
import { selectedNodeChanged } from '../../store/nodesSlice'
import { useTopology } from '../../hooks/useTopology'
import type { AppDispatch } from '../../store'

const STATE_COLORS: Record<string, string> = {
  online: '#22c55e',
  degraded: '#f59e0b',
  offline: '#ef4444',
  recovering: '#6366f1',
}

const TRANSPORT_COLORS: Record<string, string> = {
  tcp: '#3b82f6',
  udp: '#f97316',
  quic: '#a855f7',
}

const ROLE_RADIUS: Record<string, number> = {
  coordinator: 18,
  relay: 14,
  leaf: 10,
}

interface D3Node extends d3.SimulationNodeDatum {
  id: string
  role: string
  state: string
}

interface D3Edge {
  source: string | D3Node
  target: string | D3Node
  transport: string
  rtt_ms: number
}

export function TopologyGraph() {
  const svgRef = useRef<SVGSVGElement>(null)
  const dispatch = useDispatch<AppDispatch>()
  const { nodes, edges } = useTopology()

  useEffect(() => {
    const svg = d3.select(svgRef.current)
    if (!svg || nodes.length === 0) return

    const container = svgRef.current!.parentElement!
    const W = container.clientWidth || 600
    const H = container.clientHeight || 400

    svg.selectAll('*').remove()
    svg.attr('width', W).attr('height', H)

    const g = svg.append('g')

    svg.call(
      d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.3, 3]).on('zoom', evt => {
        g.attr('transform', evt.transform)
      }) as any,
    )

    const simNodes: D3Node[] = nodes.map(n => ({ id: n.id, role: n.role ?? 'leaf', state: n.state ?? 'offline' }))
    const simEdges: D3Edge[] = edges.map(e => ({
      source: e.source,
      target: e.target,
      transport: e.transport ?? 'tcp',
      rtt_ms: e.rtt_ms ?? 10,
    }))

    const sim = d3
      .forceSimulation<D3Node>(simNodes)
      .force('link', d3.forceLink<D3Node, D3Edge>(simEdges).id(d => d.id).distance(80))
      .force('charge', d3.forceManyBody().strength(-250))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide(24))

    const link = g
      .append('g')
      .selectAll<SVGLineElement, D3Edge>('line')
      .data(simEdges)
      .join('line')
      .attr('stroke', d => TRANSPORT_COLORS[d.transport] ?? '#475569')
      .attr('stroke-width', d => Math.max(1, 3 - d.rtt_ms / 100))
      .attr('stroke-opacity', 0.6)

    const nodeGroup = g
      .append('g')
      .selectAll<SVGGElement, D3Node>('g')
      .data(simNodes)
      .join('g')
      .style('cursor', 'pointer')
      .on('click', (_, d) => dispatch(selectedNodeChanged(d.id)))
      .call(
        d3
          .drag<SVGGElement, D3Node>()
          .on('start', (evt, d) => {
            if (!evt.active) sim.alphaTarget(0.3).restart()
            d.fx = d.x
            d.fy = d.y
          })
          .on('drag', (evt, d) => {
            d.fx = evt.x
            d.fy = evt.y
          })
          .on('end', (evt, d) => {
            if (!evt.active) sim.alphaTarget(0)
            d.fx = null
            d.fy = null
          }) as any,
      )

    nodeGroup
      .append('circle')
      .attr('r', d => ROLE_RADIUS[d.role] ?? 10)
      .attr('fill', d => STATE_COLORS[d.state] ?? '#475569')
      .attr('fill-opacity', 0.85)
      .attr('stroke', '#1e2533')
      .attr('stroke-width', 2)

    nodeGroup
      .append('text')
      .attr('dy', d => (ROLE_RADIUS[d.role] ?? 10) + 12)
      .attr('text-anchor', 'middle')
      .attr('fill', '#94a3b8')
      .attr('font-size', 9)
      .text(d => d.id)

    sim.on('tick', () => {
      link
        .attr('x1', d => (d.source as D3Node).x ?? 0)
        .attr('y1', d => (d.source as D3Node).y ?? 0)
        .attr('x2', d => (d.target as D3Node).x ?? 0)
        .attr('y2', d => (d.target as D3Node).y ?? 0)

      nodeGroup.attr('transform', d => `translate(${d.x ?? 0},${d.y ?? 0})`)
    })

    return () => { sim.stop() }
  }, [nodes, edges, dispatch])

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      <svg ref={svgRef} style={{ width: '100%', height: '100%' }} />
      <Legend />
    </div>
  )
}

function Legend() {
  return (
    <div style={styles.legend}>
      <div style={styles.legendTitle}>Transport</div>
      {Object.entries(TRANSPORT_COLORS).map(([k, v]) => (
        <div key={k} style={styles.legendRow}>
          <span style={{ ...styles.legendDot, background: v }} />
          {k.toUpperCase()}
        </div>
      ))}
      <div style={{ ...styles.legendTitle, marginTop: 8 }}>State</div>
      {Object.entries(STATE_COLORS).map(([k, v]) => (
        <div key={k} style={styles.legendRow}>
          <span style={{ ...styles.legendDot, background: v }} />
          {k}
        </div>
      ))}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  legend: {
    position: 'absolute',
    top: 8,
    right: 8,
    background: 'rgba(10,14,26,0.85)',
    border: '1px solid #1e2533',
    borderRadius: 6,
    padding: '8px 12px',
    fontSize: 10,
    color: '#94a3b8',
    backdropFilter: 'blur(4px)',
  },
  legendTitle: { fontWeight: 700, color: '#cbd5e1', marginBottom: 4, fontSize: 9, letterSpacing: 1 },
  legendRow: { display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 },
  legendDot: { width: 8, height: 8, borderRadius: '50%', flexShrink: 0 },
}
