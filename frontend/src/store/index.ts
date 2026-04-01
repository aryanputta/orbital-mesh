import { configureStore } from '@reduxjs/toolkit'
import nodesReducer from './nodesSlice'
import telemetryReducer from './telemetrySlice'
import anomalyReducer from './anomalySlice'
import topologyReducer from './topologySlice'

export const store = configureStore({
  reducer: {
    nodes: nodesReducer,
    telemetry: telemetryReducer,
    anomaly: anomalyReducer,
    topology: topologyReducer,
  },
})

export type RootState = ReturnType<typeof store.getState>
export type AppDispatch = typeof store.dispatch
