import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

function formatTime(ts) {
  if (!ts) return ''
  const s = String(ts)
  if (/^\d{2}:\d{2}:\d{2}/.test(s)) return s.slice(0, 8)
  try {
    const d = new Date(ts)
    if (!isNaN(d.getTime())) return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
  } catch {}
  return s.slice(11, 19) || s
}

const CHART_HEIGHT = 220

function Charts({ data }) {
  const chartData = data.map((d) => ({
    ...d,
    timeLabel: formatTime(d.timestamp),
    mw: Number(d.mw),
    viscosity: Number(d.viscosity),
    angle: Number(d.angle),
  }))

  const chartProps = {
    data: chartData,
    margin: { top: 8, right: 16, left: 8, bottom: 8 },
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-slate-800/50 p-4">
        <h3 className="text-sm font-medium text-slate-300 mb-2">MW (ppg) vs Time</h3>
        <div style={{ width: '100%', height: CHART_HEIGHT }}>
          <ResponsiveContainer width="100%" height="100%">
          <LineChart {...chartProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="timeLabel" stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.timeLabel}
              formatter={(value) => [value, 'MW (ppg)']}
            />
            <Legend />
            <Line type="monotone" dataKey="mw" stroke="#22d3ee" strokeWidth={2} dot={false} name="MW (ppg)" />
          </LineChart>
        </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-lg bg-slate-800/50 p-4">
        <h3 className="text-sm font-medium text-slate-300 mb-2">Viscosity vs Time</h3>
        <div style={{ width: '100%', height: CHART_HEIGHT }}>
          <ResponsiveContainer width="100%" height="100%">
          <LineChart {...chartProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="timeLabel" stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.timeLabel}
              formatter={(value) => [value, 'Viscosity']}
            />
            <Legend />
            <Line type="monotone" dataKey="viscosity" stroke="#a78bfa" strokeWidth={2} dot={false} name="Viscosity" />
          </LineChart>
        </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-lg bg-slate-800/50 p-4">
        <h3 className="text-sm font-medium text-slate-300 mb-2">Gate Angle vs Time</h3>
        <div style={{ width: '100%', height: CHART_HEIGHT }}>
          <ResponsiveContainer width="100%" height="100%">
          <LineChart {...chartProps}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="timeLabel" stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #475569' }}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.timeLabel}
              formatter={(value) => [value, 'Gate Angle']}
            />
            <Legend />
            <Line type="monotone" dataKey="angle" stroke="#fbbf24" strokeWidth={2} dot={false} name="Gate Angle" />
          </LineChart>
        </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}

export default Charts
