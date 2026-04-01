import { useSelector } from 'react-redux'
import { selectAnomalyEvents, selectUnreadCount } from '../store/anomalySlice'
import type { FailureClass } from '../api/types'

export function useAnomalyStream(nodeId?: string, failureClass?: FailureClass) {
  const all = useSelector(selectAnomalyEvents)
  const unreadCount = useSelector(selectUnreadCount)

  const filtered = all.filter(e => {
    if (nodeId && e.node_id !== nodeId) return false
    if (failureClass && e.failure_class !== failureClass) return false
    return true
  })

  return { events: filtered, unreadCount }
}
