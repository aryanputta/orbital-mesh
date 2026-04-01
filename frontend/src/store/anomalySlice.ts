import { createSlice, PayloadAction } from '@reduxjs/toolkit'
import type { AnomalyEvent } from '../api/types'
import type { RootState } from './index'

const MAX_EVENTS = 100

interface AnomalyState {
  events: AnomalyEvent[]
  unreadCount: number
}

const anomalySlice = createSlice({
  name: 'anomaly',
  initialState: { events: [], unreadCount: 0 } as AnomalyState,
  reducers: {
    anomalyReceived(state, action: PayloadAction<AnomalyEvent>) {
      state.events = [action.payload, ...state.events].slice(0, MAX_EVENTS)
      state.unreadCount += 1
    },
    bulkAnomaliesLoaded(state, action: PayloadAction<AnomalyEvent[]>) {
      state.events = action.payload.slice(0, MAX_EVENTS)
    },
    clearUnread(state) {
      state.unreadCount = 0
    },
  },
})

export const { anomalyReceived, bulkAnomaliesLoaded, clearUnread } = anomalySlice.actions
export const selectAnomalyEvents = (s: RootState) => s.anomaly.events
export const selectUnreadCount = (s: RootState) => s.anomaly.unreadCount
export default anomalySlice.reducer
