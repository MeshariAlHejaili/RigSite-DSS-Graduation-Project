import { useEffect, useMemo, useState } from 'react'

import socket from './api/socket.js'
import ConnectionStatus from './components/ConnectionStatus.jsx'
import HistoryPage from './components/HistoryPage.jsx'
import LiveMonitorPage from './components/LiveMonitorPage.jsx'
import ReportsPage from './components/ReportsPage.jsx'
import SettingsPage from './components/SettingsPage.jsx'
import SimulationPage from './components/SimulationPage.jsx'

const BUFFER_SIZE = 60

const ROUTES = {
  LIVE: 'live',
  RAW_DATA: 'raw-data',
  REPORTS: 'reports',
  SETTINGS: 'settings',
  SIMULATION: 'simulation',
}

const NAV_ITEMS = [
  { id: ROUTES.LIVE, label: 'Live Monitor' },
  { id: ROUTES.RAW_DATA, label: 'History / Raw Data' },
  { id: ROUTES.REPORTS, label: 'Reports' },
  { id: ROUTES.SETTINGS, label: 'Settings' },
  { id: ROUTES.SIMULATION, label: 'Simulation' },
]

function getRouteFromHash() {
  const hash = window.location.hash || '#/live'
  if (hash === '#/raw-data') return ROUTES.RAW_DATA
  if (hash === '#/reports') return ROUTES.REPORTS
  if (hash === '#/settings') return ROUTES.SETTINGS
  if (hash === '#/simulation') return ROUTES.SIMULATION
  return ROUTES.LIVE
}

function hashForRoute(route) {
  if (route === ROUTES.RAW_DATA) return '#/raw-data'
  if (route === ROUTES.REPORTS) return '#/reports'
  if (route === ROUTES.SETTINGS) return '#/settings'
  if (route === ROUTES.SIMULATION) return '#/simulation'
  return '#/live'
}

export default function App() {
  const [buffer, setBuffer] = useState([])
  const [status, setStatus] = useState(socket.getStatus())
  const [sessionCount, setSessionCount] = useState(socket.getCount())
  const [activeRoute, setActiveRoute] = useState(getRouteFromHash())
  const [showDebugStatus, setShowDebugStatus] = useState(false)

  useEffect(() => {
    const unsubscribe = socket.onMessage((message) => {
      if (message.__meta) {
        setStatus(message.status)
        setSessionCount(message.count)
        return
      }

      setBuffer((current) => {
        const next = [...current, message]
        return next.length > BUFFER_SIZE ? next.slice(next.length - BUFFER_SIZE) : next
      })
    })

    socket.connect()
    return () => {
      unsubscribe()
      socket.disconnect()
    }
  }, [])

  useEffect(() => {
    const handleHashChange = () => setActiveRoute(getRouteFromHash())
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  const latestRecord = useMemo(() => buffer[buffer.length - 1] ?? null, [buffer])
  const lastTwentyRecords = useMemo(() => buffer.slice(-20).reverse(), [buffer])
  const rawDataRows = useMemo(() => [...buffer].reverse(), [buffer])

  function handleNavigate(route) {
    window.location.hash = hashForRoute(route)
  }

  return (
    <>
      <header className="app-header">
        <div className="brand-block">
          <h1>RigLab-AI Monitor</h1>
          <p>Live mud return line telemetry</p>
        </div>
        <div className="header-actions">
          <ConnectionStatus status={status} count={sessionCount} />
        </div>
      </header>

      <main className="app-main">
        <div className="page-nav-row">
          <nav className="page-nav" aria-label="Primary">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`page-nav-button ${activeRoute === item.id ? 'page-nav-button-active' : ''}`}
                onClick={() => handleNavigate(item.id)}
              >
                {item.label}
              </button>
            ))}
          </nav>

          {activeRoute === ROUTES.LIVE && (
            <label className="debug-toggle">
              <input
                type="checkbox"
                checked={showDebugStatus}
                onChange={(event) => setShowDebugStatus(event.target.checked)}
              />
              <span>Debug / Raw Status</span>
            </label>
          )}
        </div>

        {activeRoute === ROUTES.RAW_DATA && <HistoryPage rawRows={rawDataRows} latestRecord={latestRecord} />}
        {activeRoute === ROUTES.REPORTS && <ReportsPage />}
        {activeRoute === ROUTES.SETTINGS && <SettingsPage />}
        {activeRoute === ROUTES.SIMULATION && <SimulationPage />}
        {activeRoute === ROUTES.LIVE && (
          <LiveMonitorPage
            buffer={buffer}
            latestRecord={latestRecord}
            previewRows={lastTwentyRecords}
            showDebugStatus={showDebugStatus}
          />
        )}
      </main>
    </>
  )
}
