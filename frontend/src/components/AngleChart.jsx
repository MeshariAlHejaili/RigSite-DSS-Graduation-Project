import {
  CartesianGrid,
  ComposedChart,
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

export default function AngleChart({ data }) {
  return (
    <section className="chart-card">
      <h2>Gate Angle Chart</h2>
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={data}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="timestamp" tickFormatter={formatTime} minTickGap={24} />
          <YAxis domain={[0, 90]} />
          <Tooltip
            labelFormatter={formatTime}
            formatter={(value, name) => [Number(value).toFixed(2), name]}
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
