function formatDeviation(value, unit) {
  if (value == null) return null
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(1)}${unit}`
}

function buildKickLossText(prefix, data) {
  const anglePart = formatDeviation(data.angle_deviation, '°')
  const densityPart = formatDeviation(data.density_deviation_pct, '%')

  if (data.detection_mode === 'angle_density') {
    const parts = [
      anglePart ? `Angle ${anglePart} from baseline` : null,
      densityPart ? `Density ${densityPart} from baseline` : null,
    ].filter(Boolean)
    return parts.length > 0 ? `${prefix} — ${parts.join(', ')}` : prefix
  }

  return anglePart ? `${prefix} — Angle ${anglePart} from baseline` : prefix
}

const STATE_CONFIG = {
  NORMAL: {
    background: '#2e7d32',
    text: 'NORMAL - System Stable',
  },
  KICK_RISK: {
    background: '#c62828',
    text: (data) => buildKickLossText('WARNING KICK RISK', data),
  },
  LOSS_RISK: {
    background: '#ef6c00',
    text: (data) => buildKickLossText('WARNING LOSS RISK', data),
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
