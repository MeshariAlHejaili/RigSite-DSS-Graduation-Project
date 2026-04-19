const STATE_COLORS = {
  NORMAL: 'rgba(46, 125, 50, 0.12)',
  KICK_RISK: 'rgba(198, 40, 40, 0.12)',
  LOSS_RISK: 'rgba(239, 108, 0, 0.12)',
  SENSOR_FAULT: 'rgba(97, 97, 97, 0.18)',
}

const COLUMNS = [
  { key: 'time', label: 'Time', numeric: false },
  { key: 'pressure1', label: 'P1', numeric: true },
  { key: 'pressure2', label: 'P2', numeric: true },
  { key: 'pressure_diff', label: 'Delta P', numeric: true },
  { key: 'flow', label: 'Flow', numeric: true },
  { key: 'expected_flow', label: 'Expected', numeric: true },
  { key: 'flow_deviation_pct', label: 'Deviation%', numeric: true },
  { key: 'gate_angle', label: 'Angle', numeric: true },
  { key: 'state', label: 'State', numeric: false },
  { key: 'sensor_status', label: 'Sensor Status', numeric: false },
]

function formatNumber(value) {
  return value == null ? '--' : Number(value).toFixed(2)
}

function formatTime(row) {
  const value = row.processed_at ?? row.timestamp
  if (!value) {
    return '--'
  }
  if (typeof value === 'number') {
    return new Date(value * 1000).toLocaleTimeString()
  }
  return new Date(value).toLocaleTimeString()
}

function getCellValue(row, key) {
  if (key === 'time') {
    return formatTime(row)
  }
  if (key === 'state' || key === 'sensor_status') {
    return row[key] ?? '--'
  }
  return formatNumber(row[key])
}

export default function DataTable({
  data,
  title = 'Raw Data Table',
  subtitle = '',
  emptyMessage = 'No records available yet.',
  stickyHeader = false,
}) {
  const hasData = data.length > 0

  return (
    <section className="chart-card table-card">
      <h2>{title}</h2>
      {subtitle && <p className="table-subtitle">{subtitle}</p>}
      <div className="table-scroll">
        <table className={`data-table ${stickyHeader ? 'data-table-sticky' : ''}`}>
          <thead>
            <tr>
              {COLUMNS.map((column) => (
                <th key={column.key} className={column.numeric ? 'data-table-number' : ''}>
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {hasData ? (
              data.map((row, index) => (
                <tr key={`${row.timestamp}-${index}`} style={{ background: STATE_COLORS[row.state] ?? 'transparent' }}>
                  {COLUMNS.map((column) => (
                    <td key={`${column.key}-${index}`} className={column.numeric ? 'data-table-number' : ''}>
                      {getCellValue(row, column.key)}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td className="data-table-empty" colSpan={COLUMNS.length}>
                  {emptyMessage}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
