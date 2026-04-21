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

export default function ViscosityChart({ data }) {
  return (
    <section className="chart-card">
      <h2>Viscosity Chart</h2>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="timestamp" tickFormatter={formatTime} minTickGap={24} />
          <YAxis />
          <Tooltip labelFormatter={formatTime} formatter={(value) => Number(value).toFixed(3)} />
          <Legend />
          <Line type="monotone" dataKey="viscosity" name="Viscosity" stroke="#6a1b9a" strokeWidth={3} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </section>
  )
}
