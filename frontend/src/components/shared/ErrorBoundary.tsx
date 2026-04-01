import { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback ?? (
          <div style={{ padding: '1rem', color: '#ef4444', background: '#1e1e2e', borderRadius: '8px' }}>
            <strong>Component error:</strong> {this.state.error?.message}
          </div>
        )
      )
    }
    return this.props.children
  }
}
