import { useEffect, useMemo, useState } from 'react'

import socket from './api/socket.js'
import AngleChart from './components/AngleChart.jsx'
import ConnectionStatus from './components/ConnectionStatus.jsx'
import DataTable from './components/DataTable.jsx'
import DetectionSummary from './components/DetectionSummary.jsx'
import FlowChart from './components/FlowChart.jsx'
import PressureChart from './components/PressureChart.jsx'
import ReportControls from './components/ReportControls.jsx'
import SettingsPage from './components/SettingsPage.jsx'
import SimulatorControls from './components/SimulatorControls.jsx'
import StateBadge from './components/StateBadge.jsx'
import AngleTestUpload from './components/AngleTestUpload.jsx'

const BUFFER_SIZE = 60
const DASHBOARD_ROUTE = 'dashboard'
const RAW_DATA_ROUTE = 'raw-data'
const SETTINGS_ROUTE = 'settings'
const FILTER_ALL = 'ALL'

function getRouteFromHash() {
  if (window.location.hash === '#/raw-data') return RAW_DATA_ROUTE
  if (window.location.hash === '#/settings') return SETTINGS_ROUTE
  return DASHBOARD_ROUTE
}

function formatLastUpdate(value) {
  if (!value) {
    return '--'
  }
  if (typeof value === 'number') {
    return new Date(value * 1000).toLocaleTimeString()
  }
  return new Date(value).toLocaleTimeString()
}

export default function App() {
  const [buffer, setBuffer] = useState([])
  const [status, setStatus] = useState(socket.getStatus())
  const [sessionCount, setSessionCount] = useState(socket.getCount())
  const [route, setRoute] = useState(getRouteFromHash())
  const [stateFilter, setStateFilter] = useState(FILTER_ALL)
  const [sensorFilter, setSensorFilter] = useState(FILTER_ALL)
  const [searchQuery, setSearchQuery] = useState('')

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
    const handleHashChange = () => {
      setRoute(getRouteFromHash())
    }
    window.addEventListener('hashchange', handleHashChange)
    return () => {
      window.removeEventListener('hashchange', handleHashChange)
    }
  }, [])

  const latestRecord = buffer[buffer.length - 1] ?? null
  const lastTwentyRecords = buffer.slice(-20).reverse()
  const rawDataRows = [...buffer].reverse()
  const isRawDataPage = route === RAW_DATA_ROUTE
  const isSettingsPage = route === SETTINGS_ROUTE
  const isDashboard = route === DASHBOARD_ROUTE

  const stateOptions = useMemo(() => {
    const values = [...new Set(rawDataRows.map((row) => row.state).filter(Boolean))]
    return [FILTER_ALL, ...values]
  }, [rawDataRows])
  const sensorOptions = useMemo(() => {
    const values = [...new Set(rawDataRows.map((row) => row.sensor_status).filter(Boolean))]
    return [FILTER_ALL, ...values]
  }, [rawDataRows])
  const filteredRawDataRows = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase()
    return rawDataRows.filter((row) => {
      if (stateFilter !== FILTER_ALL && row.state !== stateFilter) {
        return false
      }
      if (sensorFilter !== FILTER_ALL && row.sensor_status !== sensorFilter) {
        return false
      }
      if (!normalizedQuery) {
        return true
      }
      const searchableText = [
        row.state,
        row.sensor_status,
        row.processed_at,
        row.timestamp,
        row.pressure1,
        row.pressure2,
        row.pressure_diff,
        row.flow,
        row.expected_flow,
        row.flow_deviation_pct,
        row.gate_angle,
      ]
        .filter((value) => value !== null && value !== undefined)
        .map((value) => String(value).toLowerCase())
        .join(' ')
      return searchableText.includes(normalizedQuery)
    })
  }, [rawDataRows, searchQuery, sensorFilter, stateFilter])
  const hasActiveFilters = stateFilter !== FILTER_ALL || sensorFilter !== FILTER_ALL || searchQuery.trim() !== ''

  function handleTogglePage() {
    if (isRawDataPage) {
      window.location.hash = ''
      return
    }
    window.location.hash = '/raw-data'
  }

  function handleResetFilters() {
    setStateFilter(FILTER_ALL)
    setSensorFilter(FILTER_ALL)
    setSearchQuery('')
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
          <button
            type="button"
            className={`header-nav-button ${isSettingsPage ? 'header-nav-button-active' : ''}`}
            onClick={() => {
              window.location.hash = isSettingsPage ? '' : '/settings'
            }}
          >
            {isSettingsPage ? 'Back To Dashboard' : 'Settings'}
          </button>
          <button type="button" className="header-nav-button" onClick={handleTogglePage}>
            {isRawDataPage ? 'Back To Dashboard' : 'Open Raw Data'}
          </button>
        </div>
      </header>

      <main className="app-main">
        {isSettingsPage ? (
          <SettingsPage />
        ) : isRawDataPage ? (
          <>
            <section className="chart-card raw-data-hero">
              <div>
                <h2>Raw Data Workspace</h2>
                <p className="raw-data-description">
                  Review the latest telemetry records in a full-width table designed for quick scanning and incident
                  investigation.
                </p>
              </div>
              <div className="raw-data-meta">
                <span className="raw-data-pill">
                  Showing: {filteredRawDataRows.length} / {rawDataRows.length}
                </span>
                <span className="raw-data-pill">
                  Last update: {formatLastUpdate(latestRecord?.processed_at ?? latestRecord?.timestamp)}
                </span>
              </div>
            </section>
            <section className="chart-card raw-data-filters">
              <div className="raw-filter-grid">
                <label className="raw-filter-field">
                  State
                  <select
                    className="raw-filter-input"
                    value={stateFilter}
                    onChange={(event) => setStateFilter(event.target.value)}
                  >
                    <option value={FILTER_ALL}>All States</option>
                    {stateOptions
                      .filter((option) => option !== FILTER_ALL)
                      .map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                  </select>
                </label>
                <label className="raw-filter-field">
                  Sensor Status
                  <select
                    className="raw-filter-input"
                    value={sensorFilter}
                    onChange={(event) => setSensorFilter(event.target.value)}
                  >
                    <option value={FILTER_ALL}>All Sensors</option>
                    {sensorOptions
                      .filter((option) => option !== FILTER_ALL)
                      .map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                  </select>
                </label>
                <label className="raw-filter-field">
                  Search
                  <input
                    type="search"
                    className="raw-filter-input"
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    placeholder="Search state, sensor, or values..."
                  />
                </label>
              </div>
              <div className="raw-filter-actions">
                <span className="raw-filter-hint">Use filters to triage incidents faster.</span>
                {hasActiveFilters && (
                  <button type="button" className="raw-filter-reset" onClick={handleResetFilters}>
                    Clear Filters
                  </button>
                )}
              </div>
            </section>
            <DataTable
              data={filteredRawDataRows}
              title="Live Telemetry Records"
              subtitle="Newest records appear first. Sticky headers keep labels visible while scrolling."
              emptyMessage={
                hasActiveFilters
                  ? 'No records match the current filters. Adjust filters and try again.'
                  : 'No telemetry data yet. Start ingesting data to populate this page.'
              }
              stickyHeader
            />
          </>
        ) : (
          <>
            <StateBadge data={latestRecord} />

            <section className="charts-row">
              <FlowChart data={buffer} />
              <PressureChart data={buffer} />
            </section>

            <AngleChart data={buffer} />
            <DetectionSummary buffer={buffer} />
            <AngleTestUpload />
            <ReportControls />
            <SimulatorControls />
            <DataTable
              data={lastTwentyRecords}
              title="Quick Raw Data Preview"
              subtitle="Showing the latest 20 records. Use Open Raw Data for the complete view."
              emptyMessage="No records to preview yet."
            />
          </>
        )}
      </main>
    </>
  )
}
