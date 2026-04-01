import { useSelector } from 'react-redux'
import { selectTopology, selectTopologyAge } from '../store/topologySlice'
import { selectAllNodes } from '../store/nodesSlice'

export function useTopology() {
  const snapshot = useSelector(selectTopology)
  const lastUpdated = useSelector(selectTopologyAge)
  const registryNodes = useSelector(selectAllNodes)

  const mergedNodes = snapshot
    ? snapshot.nodes.map(n => {
        const registry = registryNodes.find(r => r.node_id === n.id)
        return { ...n, state: registry?.state ?? n.state }
      })
    : []

  return { snapshot, lastUpdated, nodes: mergedNodes, edges: snapshot?.edges ?? [] }
}
