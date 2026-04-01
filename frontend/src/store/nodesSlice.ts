import { createSlice, createEntityAdapter, PayloadAction } from '@reduxjs/toolkit'
import type { NodeInfo } from '../api/types'
import type { RootState } from './index'

const adapter = createEntityAdapter<NodeInfo>({ selectId: n => n.node_id })

const nodesSlice = createSlice({
  name: 'nodes',
  initialState: adapter.getInitialState({ selectedNodeId: null as string | null }),
  reducers: {
    allNodesLoaded: adapter.setAll,
    nodeUpdated: adapter.upsertOne,
    nodeStateChanged(state, action: PayloadAction<{ node_id: string; state: NodeInfo['state']; transport?: string }>) {
      const { node_id, state: newState, transport } = action.payload
      const existing = state.entities[node_id]
      if (existing) {
        existing.state = newState
        if (transport) existing.current_transport = transport as NodeInfo['current_transport']
      }
    },
    selectedNodeChanged(state, action: PayloadAction<string | null>) {
      state.selectedNodeId = action.payload
    },
  },
})

export const { allNodesLoaded, nodeUpdated, nodeStateChanged, selectedNodeChanged } = nodesSlice.actions
export const { selectAll: selectAllNodes, selectById: selectNodeById } = adapter.getSelectors<RootState>(s => s.nodes)
export const selectSelectedNodeId = (s: RootState) => s.nodes.selectedNodeId
export default nodesSlice.reducer
