import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

function formatTime(ts) {
  if (!ts) return ''
  const s = String(ts)
  if (/^\d{2}:\d{2}:\d{2}/.test(s)) return s.slice(0, 8)
  try {
    const d = new Date(ts)
    if (!isNaN(d.getTime())) {
      return d.toLocaleTimeString('en-GB', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      })
    }
  } catch {}
  return s.slice(11, 19) || s
}

function formatYValue(dataKey, value) {
  if (value == null || Number.isNaN(Number(value))) return '—'
  const n = Number(value)
  if (dataKey === 'mw') return n.toFixed(2)
  return n.toFixed(1)
}

const CHART_HEIGHT = 268

const METRIC_CONFIG = {
  mw: {
    title: 'MW vs Time',
    dataKey: 'mw',
    stroke: '#22d3ee',
    seriesName: 'MW (ppg)',
  },
  viscosity: {
    title: 'Viscosity vs Time',
    dataKey: 'viscosity',
    stroke: '#a78bfa',
    seriesName: 'Viscosity',
  },
  angle: {
    title: 'Gate Angle vs Time',
    dataKey: 'angle',
    stroke: '#fbbf24',
    seriesName: 'Gate Angle',
  },
}

function ChartTooltip({ active, payload, cfg }) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  const raw = payload[0].value
  const timeStr = row?.timeLabel || formatTime(row?.timestamp)
  const display = formatYValue(cfg.dataKey, raw)

  return (
    <div className="rounded-xl border border-slate-500/35 bg-slate-950/95 px-3.5 py-2.5 shadow-2xl ring-1 ring-white/10 backdrop-blur-md">
      <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-slate-500">
        Time
      </p>
      <p className="mt-0.5 font-mono text-[13px] tabular-nums tracking-tight text-slate-100">
        {timeStr}
      </p>
      <p className="mt-2.5 text-[10px] font-medium uppercase tracking-[0.16em] text-slate-500">
        {cfg.seriesName}
      </p>
      <p
        className="mt-0.5 font-mono text-[13px] font-medium tabular-nums tracking-tight"
        style={{ color: cfg.stroke }}
      >
        {display}
      </p>
    </div>
  )
}

const GRID_STROKE = 'rgba(148, 163, 184, 0.07)'
const AXIS_TICK = { fill: '#94a3b8', fontSize: 11, fontWeight: 400 }

function Charts({ data, metric = 'mw' }) {
  const cfg = METRIC_CONFIG[metric] ?? METRIC_CONFIG.mw

  const chartData = data.map((d) => ({
    ...d,
    timeLabel: formatTime(d.timestamp),
    mw: Number(d.mw),
    viscosity: Number(d.viscosity),
    angle: Number(d.angle),
  }))

  const chartMargins = { top: 8, right: 8, left: 4, bottom: 4 }

  const yTickFormatter = (v) => formatYValue(cfg.dataKey, v)

  return (
    <div className="rounded-2xl border border-white/[0.07] bg-slate-950/45 p-5 shadow-[0_24px_48px_-12px_rgba(0,0,0,0.55)] ring-1 ring-white/[0.04] backdrop-blur-md md:p-6">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-x-4 gap-y-1 border-b border-white/[0.06] pb-3">
        <h3 className="text-sm font-semibold tracking-tight text-slate-200">{cfg.title}</h3>
        <span className="text-xs font-light tracking-[0.06em] text-slate-400">
          {cfg.seriesName}
        </span>
      </div>
      <div style={{ width: '100%', height: CHART_HEIGHT }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={chartMargins}>
            <CartesianGrid
              stroke={GRID_STROKE}
              strokeDasharray="1 6"
              vertical
              horizontal
              syncWithTicks
            />
            <XAxis
              dataKey="timeLabel"
              axisLine={{ stroke: 'rgba(148, 163, 184, 0.2)' }}
              tickLine={{ stroke: 'rgba(148, 163, 184, 0.25)' }}
              tick={AXIS_TICK}
              tickMargin={10}
              minTickGap={36}
              interval="preserveStartEnd"
              height={34}
            />
            <YAxis
              axisLine={{ stroke: 'rgba(148, 163, 184, 0.2)' }}
              tickLine={{ stroke: 'rgba(148, 163, 184, 0.25)' }}
              tick={AXIS_TICK}
              tickMargin={8}
              tickCount={5}
              width={48}
              tickFormatter={yTickFormatter}
              domain={['auto', 'auto']}
            />
            <Tooltip
              content={(tooltipProps) => <ChartTooltip {...tooltipProps} cfg={cfg} />}
              cursor={{
                stroke: 'rgba(148, 163, 184, 0.35)',
                strokeWidth: 1,
                strokeDasharray: '4 4',
              }}
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey={cfg.dataKey}
              stroke={cfg.stroke}
              strokeWidth={2}
              dot={false}
              activeDot={{
                r: 6,
                strokeWidth: 2,
                stroke: '#0f172a',
                fill: cfg.stroke,
              }}
              name={cfg.seriesName}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export const METRIC_ORDER = ['mw', 'viscosity', 'angle']

export { METRIC_CONFIG }

export default Charts
