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

export default function MudWeightChart({ data }) {
  return (
    <section className="chart-card">
      <h2>Mud Weight Chart</h2>
      <p className="chart-subtitle">PPG — active display weight, normal baseline, and with-cuttings estimate</p>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="timestamp" tickFormatter={formatTime} minTickGap={24} />
          <YAxis />
          <Tooltip labelFormatter={formatTime} formatter={(value) => Number(value).toFixed(3)} />
          <Legend />
          <Line type="monotone" dataKey="mud_weight" name="Mud Weight" stroke="#1565c0" strokeWidth={3} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="normal_mud_weight" name="Normal" stroke="#6d6d6d" strokeDasharray="7 5" dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="mud_weight_with_cuttings" name="With Cuttings" stroke="#ef6c00" strokeDasharray="3 3" dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </section>
  )
}
