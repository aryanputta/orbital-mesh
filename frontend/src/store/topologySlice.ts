import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { TopologySnapshot } from '../api/types'
import type { RootState } from './index'

interface TopologyState {
  snapshot: TopologySnapshot | null
  lastUpdated: number | null
}

const topologySlice = createSlice({
  name: 'topology',
  initialState: { snapshot: null, lastUpdated: null } as TopologyState,
  reducers: {
    topologyUpdated(state, action: PayloadAction<TopologySnapshot>) {
      state.snapshot = action.payload
      state.lastUpdated = Date.now()
    },
  },
})

export const { topologyUpdated } = topologySlice.actions
export const selectTopology = (s: RootState) => s.topology.snapshot
export const selectTopologyAge = (s: RootState) => s.topology.lastUpdated
export default topologySlice.reducer
