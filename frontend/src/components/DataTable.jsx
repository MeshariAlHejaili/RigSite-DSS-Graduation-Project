const STATE_COLORS = {
  NORMAL: 'rgba(46, 125, 50, 0.12)',
  KICK_RISK: 'rgba(198, 40, 40, 0.12)',
  LOSS_RISK: 'rgba(239, 108, 0, 0.12)',
  SENSOR_FAULT: 'rgba(97, 97, 97, 0.18)',
}

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

export default function DataTable({ data }) {
  return (
    <section className="chart-card table-card">
      <h2>Raw Data Table</h2>
      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>P1</th>
              <th>P2</th>
              <th>Delta P</th>
              <th>Flow</th>
              <th>Expected</th>
              <th>Deviation%</th>
              <th>Angle</th>
              <th>State</th>
              <th>Sensor Status</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, index) => (
              <tr key={`${row.timestamp}-${index}`} style={{ background: STATE_COLORS[row.state] ?? 'transparent' }}>
                <td>{formatTime(row)}</td>
                <td>{formatNumber(row.pressure1)}</td>
                <td>{formatNumber(row.pressure2)}</td>
                <td>{formatNumber(row.pressure_diff)}</td>
                <td>{formatNumber(row.flow)}</td>
                <td>{formatNumber(row.expected_flow)}</td>
                <td>{formatNumber(row.flow_deviation_pct)}</td>
                <td>{formatNumber(row.gate_angle)}</td>
                <td>{row.state}</td>
                <td>{row.sensor_status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
