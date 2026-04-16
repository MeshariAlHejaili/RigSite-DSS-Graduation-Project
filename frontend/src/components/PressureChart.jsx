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

export default function PressureChart({ data }) {
  return (
    <section className="chart-card">
      <h2>Pressure Chart</h2>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="timestamp" tickFormatter={formatTime} minTickGap={24} />
          <YAxis />
          <Tooltip labelFormatter={formatTime} formatter={(value) => Number(value).toFixed(2)} />
          <Legend />
          <Line type="monotone" dataKey="pressure1" name="P1 Upstream" stroke="#0d47a1" strokeWidth={3} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="pressure2" name="P2 Downstream" stroke="#42a5f5" strokeWidth={3} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="pressure_diff" name="Delta P" stroke="#c62828" strokeDasharray="6 4" dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </section>
  )
}
