const STATE_CONFIG = {
  NORMAL: {
    background: '#2e7d32',
    text: 'NORMAL - System Stable',
  },
  KICK_RISK: {
    background: '#c62828',
    text: (data) => `WARNING KICK RISK - Flow High by ${data.flow_deviation_pct.toFixed(1)}%`,
  },
  LOSS_RISK: {
    background: '#ef6c00',
    text: (data) => `WARNING LOSS RISK - Flow Low by ${Math.abs(data.flow_deviation_pct).toFixed(1)}%`,
  },
  SENSOR_FAULT: {
    background: '#616161',
    text: 'WARNING SENSOR FAULT - Check Hardware',
  },
}

function formatTime(value) {
  if (!value) {
    return '--'
  }
  return new Date(value).toLocaleTimeString()
}

export default function StateBadge({ data }) {
  if (!data) {
    return (
      <section className="state-badge waiting-state">
        <span className="state-title">Waiting for live data...</span>
      </section>
    )
  }

  const config = STATE_CONFIG[data.state] ?? STATE_CONFIG.SENSOR_FAULT
  const title = typeof config.text === 'function' ? config.text(data) : config.text
  return (
    <section className="state-badge" style={{ background: config.background }}>
      <span className="state-title">{title}</span>
      <span className="state-subtitle">
        Last update: {formatTime(data.processed_at)} | Sensor status: {data.sensor_status}
      </span>
    </section>
  )
}
