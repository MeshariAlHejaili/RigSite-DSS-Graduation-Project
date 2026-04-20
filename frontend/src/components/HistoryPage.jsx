import { useMemo, useState } from 'react'

import DataTable from './DataTable.jsx'

const FILTER_ALL = 'ALL'

function formatLastUpdate(value) {
  if (!value) {
    return '--'
  }
  if (typeof value === 'number') {
    return new Date(value * 1000).toLocaleTimeString()
  }
  return new Date(value).toLocaleTimeString()
}

export default function HistoryPage({ rawRows, latestRecord }) {
  const [stateFilter, setStateFilter] = useState(FILTER_ALL)
  const [sensorFilter, setSensorFilter] = useState(FILTER_ALL)
  const [searchQuery, setSearchQuery] = useState('')

  const stateOptions = useMemo(() => {
    const values = [...new Set(rawRows.map((row) => row.state).filter(Boolean))]
    return [FILTER_ALL, ...values]
  }, [rawRows])

  const sensorOptions = useMemo(() => {
    const values = [...new Set(rawRows.map((row) => row.sensor_status).filter(Boolean))]
    return [FILTER_ALL, ...values]
  }, [rawRows])

  const filteredRows = useMemo(() => {
    const normalizedQuery = searchQuery.trim().toLowerCase()

    return rawRows.filter((row) => {
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
        row.viscosity,
        row.normal_mud_weight,
        row.mud_weight_with_cuttings,
      ]
        .filter((value) => value !== null && value !== undefined)
        .map((value) => String(value).toLowerCase())
        .join(' ')

      return searchableText.includes(normalizedQuery)
    })
  }, [rawRows, searchQuery, sensorFilter, stateFilter])

  const hasActiveFilters = stateFilter !== FILTER_ALL || sensorFilter !== FILTER_ALL || searchQuery.trim() !== ''

  function handleResetFilters() {
    setStateFilter(FILTER_ALL)
    setSensorFilter(FILTER_ALL)
    setSearchQuery('')
  }

  return (
    <>
      <section className="chart-card raw-data-hero">
        <div>
          <h2>History / Raw Data</h2>
          <p className="raw-data-description">
            Review full telemetry history with filter controls for faster incident triage.
          </p>
        </div>
        <div className="raw-data-meta">
          <span className="raw-data-pill">
            Showing: {filteredRows.length} / {rawRows.length}
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
          <span className="raw-filter-hint">Use filters to isolate anomalies quickly.</span>
          {hasActiveFilters && (
            <button type="button" className="raw-filter-reset" onClick={handleResetFilters}>
              Clear Filters
            </button>
          )}
        </div>
      </section>

      <DataTable
        data={filteredRows}
        title="Telemetry History Table"
        subtitle="Newest records appear first. Sticky headers remain visible while scrolling."
        emptyMessage={
          hasActiveFilters
            ? 'No records match the current filters. Adjust filters and try again.'
            : 'No telemetry history available yet.'
        }
        stickyHeader
      />
    </>
  )
}
