import type { WebSocketMessage } from './types'

type MessageHandler<T = unknown> = (msg: WebSocketMessage<T>) => void
type TopicHandlers = Map<string, MessageHandler[]>

const BASE_BACKOFF_MS = 1_000
const MAX_BACKOFF_MS = 30_000

export class OrbitalWebSocket {
  private ws: WebSocket | null = null
  private handlers: TopicHandlers = new Map()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private backoffMs = BASE_BACKOFF_MS
  private closed = false

  constructor(private readonly url: string) {}

  connect(): void {
    if (this.closed) return
    try {
      this.ws = new WebSocket(this.url)
      this.ws.onopen = () => {
        this.backoffMs = BASE_BACKOFF_MS
      }
      this.ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data) as WebSocketMessage
          const topicHandlers = this.handlers.get(msg.topic) ?? []
          const wildcardHandlers = this.handlers.get('*') ?? []
          ;[...topicHandlers, ...wildcardHandlers].forEach(h => h(msg))
        } catch {
          // malformed message
        }
      }
      this.ws.onclose = () => {
        if (!this.closed) this.scheduleReconnect()
      }
      this.ws.onerror = () => {
        this.ws?.close()
      }
    } catch {
      this.scheduleReconnect()
    }
  }

  subscribe<T = unknown>(topic: string, handler: MessageHandler<T>): () => void {
    const list = this.handlers.get(topic) ?? []
    list.push(handler as MessageHandler)
    this.handlers.set(topic, list)
    return () => {
      const updated = (this.handlers.get(topic) ?? []).filter(h => h !== handler)
      this.handlers.set(topic, updated)
    }
  }

  disconnect(): void {
    this.closed = true
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    this.ws?.close()
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  private scheduleReconnect(): void {
    if (this.closed) return
    this.reconnectTimer = setTimeout(() => {
      this.backoffMs = Math.min(this.backoffMs * 2, MAX_BACKOFF_MS)
      this.connect()
    }, this.backoffMs)
  }
}
