const STATE_COLORS = {
  NORMAL: 'rgba(46, 125, 50, 0.10)',
  KICK_RISK: 'rgba(198, 40, 40, 0.10)',
  LOSS_RISK: 'rgba(239, 108, 0, 0.10)',
  SENSOR_FAULT: 'rgba(97, 97, 97, 0.14)',
}

const STATE_CHIP_CLASSES = {
  NORMAL: 'state-chip state-chip-normal',
  KICK_RISK: 'state-chip state-chip-kick',
  LOSS_RISK: 'state-chip state-chip-loss',
  SENSOR_FAULT: 'state-chip state-chip-fault',
}

const COLUMNS = [
  { key: 'time', label: 'Time', numeric: false },
  { key: 'pressure1', label: 'P1 (psi)', numeric: true, decimals: 3 },
  { key: 'pressure2', label: 'P2 (psi)', numeric: true, decimals: 3 },
  { key: 'pressure_diff', label: 'Delta P (psi)', numeric: true, decimals: 3 },
  { key: 'flow', label: 'Flow (L/min)', numeric: true },
  { key: 'expected_flow', label: 'Expected Flow (L/min)', numeric: true },
  { key: 'flow_deviation_pct', label: 'Deviation (%)', numeric: true },
  { key: 'gate_angle', label: 'Gate Angle (deg)', numeric: true },
  { key: 'viscosity', label: 'Viscosity (Pa*s)', numeric: true, placeholder: true },
  { key: 'normal_mud_weight', label: 'Mud Weight (ppg)', numeric: true, placeholder: true },
  {
    key: 'mud_weight_with_cuttings',
    label: 'Mud Weight w/ Cuttings (ppg)',
    numeric: true,
    placeholder: true,
  },
  { key: 'state', label: 'State', numeric: false },
  { key: 'sensor_status', label: 'Sensor Status', numeric: false },
]

function formatNumber(value, fallback = '--', decimals = 2) {
  return value == null ? fallback : Number(value).toFixed(decimals)
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

function StateChip({ value }) {
  if (!value) return '--'
  const chipClass = STATE_CHIP_CLASSES[value] ?? 'state-chip'
  const label = value.replace(/_/g, ' ')
  return <span className={chipClass}>{label}</span>
}

function getCellValue(row, column) {
  if (column.key === 'time') {
    return formatTime(row)
  }

  if (column.key === 'state') {
    return <StateChip value={row.state} />
  }

  if (column.key === 'sensor_status') {
    return row[column.key] ?? '--'
  }

  if (column.placeholder) {
    return formatNumber(row[column.key], '-', column.decimals ?? 2)
  }

  return formatNumber(row[column.key], '--', column.decimals ?? 2)
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
                <tr
                  key={`${row.timestamp}-${index}`}
                  style={STATE_COLORS[row.state] ? { background: STATE_COLORS[row.state] } : undefined}
                >
                  {COLUMNS.map((column) => (
                    <td key={`${column.key}-${index}`} className={column.numeric ? 'data-table-number' : ''}>
                      {getCellValue(row, column)}
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
