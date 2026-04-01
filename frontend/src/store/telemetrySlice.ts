import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { TelemetryFrame } from '../api/types'
import type { RootState } from './index'

const MAX_FRAMES_PER_NODE = 100

interface TelemetryState {
  frames: Record<string, TelemetryFrame[]>
}

const telemetrySlice = createSlice({
  name: 'telemetry',
  initialState: { frames: {} } as TelemetryState,
  reducers: {
    telemetryReceived(state, action: PayloadAction<TelemetryFrame>) {
      const { node_id } = action.payload
      const existing = state.frames[node_id] ?? []
      const updated = [...existing, action.payload]
      state.frames[node_id] = updated.slice(-MAX_FRAMES_PER_NODE)
    },
    bulkTelemetryLoaded(state, action: PayloadAction<{ node_id: string; frames: TelemetryFrame[] }>) {
      state.frames[action.payload.node_id] = action.payload.frames.slice(-MAX_FRAMES_PER_NODE)
    },
  },
})

export const { telemetryReceived, bulkTelemetryLoaded } = telemetrySlice.actions
export const selectFramesForNode = (nodeId: string) => (s: RootState): TelemetryFrame[] =>
  s.telemetry.frames[nodeId] ?? []
export const selectLatestFrame = (nodeId: string) => (s: RootState): TelemetryFrame | undefined => {
  const frames = s.telemetry.frames[nodeId]
  return frames?.[frames.length - 1]
}
export default telemetrySlice.reducer
