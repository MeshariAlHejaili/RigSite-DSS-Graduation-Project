import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

function formatTime(value) {
  if (typeof value === 'number') {
    return new Date(value * 1000).toLocaleTimeString()
  }
  return new Date(value).toLocaleTimeString()
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) {
    return null
  }

  const point = payload[0].payload
  return (
    <div className="chart-tooltip">
      <div>{formatTime(label)}</div>
      <div>Actual: {point.flow.toFixed(2)} L/min</div>
      <div>Expected: {point.expected_flow.toFixed(2)} L/min</div>
      <div>Deviation: {point.flow_deviation_pct.toFixed(2)}%</div>
    </div>
  )
}

export default function FlowChart({ data }) {
  const chartData = data.map((point) => ({
    ...point,
    high_threshold: point.expected_flow * 1.15,
    low_threshold: point.expected_flow * 0.85,
  }))

  return (
    <section className="chart-card">
      <h2>Flow Chart</h2>
      <p className="chart-subtitle">L/min — actual vs. expected with ±15% thresholds</p>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="timestamp" tickFormatter={formatTime} minTickGap={24} />
          <YAxis />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Line type="monotone" dataKey="flow" name="Actual Flow" stroke="#1565c0" strokeWidth={3} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="expected_flow" name="Expected Flow" stroke="#6d6d6d" strokeDasharray="7 5" dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="high_threshold" name="+15% Threshold" stroke="#d32f2f" strokeDasharray="3 3" dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="low_threshold" name="-15% Threshold" stroke="#fb8c00" strokeDasharray="3 3" dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </section>
  )
}
