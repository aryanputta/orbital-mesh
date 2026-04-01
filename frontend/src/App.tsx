import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Provider } from 'react-redux'
import { store } from './store'
import { AppShell } from './components/layout/AppShell'
import { Dashboard } from './pages/Dashboard'
import { ProtocolAnalysis } from './pages/ProtocolAnalysis'
import { ErrorBoundary } from './components/shared/ErrorBoundary'

export default function App() {
  return (
    <Provider store={store}>
      <BrowserRouter>
        <ErrorBoundary>
          <Routes>
            <Route element={<AppShell />}>
              <Route index element={<Dashboard />} />
              <Route path="protocols" element={<ProtocolAnalysis />} />
            </Route>
          </Routes>
        </ErrorBoundary>
      </BrowserRouter>
    </Provider>
  )
}
