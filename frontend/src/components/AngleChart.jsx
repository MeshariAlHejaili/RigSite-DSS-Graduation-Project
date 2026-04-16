import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
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

function buildChartData(data) {
  return data.map((point) => ({
    ...point,
    confidence_band: (point.gate_angle ?? 0) * (point.angle_confidence ?? 0),
  }))
}

export default function AngleChart({ data }) {
  return (
    <section className="chart-card">
      <h2>Gate Angle Chart</h2>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={buildChartData(data)}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="timestamp" tickFormatter={formatTime} minTickGap={24} />
          <YAxis domain={[0, 90]} />
          <Tooltip
            labelFormatter={formatTime}
            formatter={(value, name, item) => {
              if (name === 'Angle Confidence Band') {
                return [`${((item.payload.angle_confidence ?? 0) * 100).toFixed(0)}%`, 'Angle Confidence']
              }
              return [Number(value).toFixed(2), name]
            }}
          />
          <Legend />
          <Area
            type="monotone"
            dataKey="confidence_band"
            name="Angle Confidence Band"
            stroke="#ffb74d"
            fill="#ffcc80"
            fillOpacity={0.35}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey="gate_angle"
            name="Gate Angle"
            stroke="#ef6c00"
            strokeWidth={3}
            dot={false}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </section>
  )
}
