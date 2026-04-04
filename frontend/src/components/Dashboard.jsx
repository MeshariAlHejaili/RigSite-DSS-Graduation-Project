import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import Charts, { METRIC_CONFIG, METRIC_ORDER } from './Charts'
import AlertsCenter from './AlertsCenter'

const WS_URL = 'ws://localhost:8000/ws'
const UPLOAD_URL = 'http://localhost:8000/upload'
const MAX_POINTS = 30 // 10 min window at 20s interval
const POINTS_5_MIN = 15 // 5 min = 15 points
const ANGLE_THRESHOLD_KICK = 15
const ANGLE_THRESHOLD_LOSS = -15

function deriveSituation(data) {
  if (data.length < MAX_POINTS) return 'Normal'
  const prev5 = data.slice(0, POINTS_5_MIN)
  const new5 = data.slice(-POINTS_5_MIN)
  const avgPrev = prev5.reduce((s, p) => s + (p.angle ?? 0), 0) / prev5.length
  const avgNew = new5.reduce((s, p) => s + (p.angle ?? 0), 0) / new5.length
  const delta = avgNew - avgPrev
  if (delta > ANGLE_THRESHOLD_KICK) return 'Kick'
  if (delta < ANGLE_THRESHOLD_LOSS) return 'Loss'
  return 'Normal'
}

function Dashboard() {
  const [data, setData] = useState([])
  const [uploading, setUploading] = useState(false)
  const [uploadMessage, setUploadMessage] = useState(null)
  const [wsStatus, setWsStatus] = useState('disconnected')
  const [streamAfterUpload, setStreamAfterUpload] = useState(false)
  const [wsKey, setWsKey] = useState(0)
  const [selectedMetric, setSelectedMetric] = useState('mw')
  const [alertsOpen, setAlertsOpen] = useState(false)
  const wsRef = useRef(null)
  const fileInputRef = useRef(null)

  const situation = useMemo(() => deriveSituation(data), [data])

  const addPoint = useCallback((point) => {
    setData((prev) => {
      const next = [...prev, point]
      if (next.length > MAX_POINTS) next.shift()
      return next
    })
  }, [])

  useEffect(() => {
    if (!streamAfterUpload) return
    setWsStatus('connecting')
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => setWsStatus('connected')
    ws.onclose = () => setWsStatus('disconnected')
    ws.onerror = () => setWsStatus('disconnected')

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        if (payload.status === 'no_data') return
        addPoint({
          timestamp: payload.timestamp,
          mw: payload.mw,
          viscosity: payload.viscosity,
          angle: payload.angle,
          situation: payload.situation,
        })
      } catch (_) {}
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [addPoint, streamAfterUpload, wsKey])

  const handleUpload = async (e) => {
    const file = e?.target?.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadMessage(null)
    const formData = new FormData()
    formData.append('file', file)
    try {
      const res = await fetch(UPLOAD_URL, { method: 'POST', body: formData })
      const json = await res.json().catch(() => ({}))
      if (res.ok) {
        setUploadMessage(`Uploaded: ${json.rows_saved ?? 0} rows. Streaming…`)
        setData([])
        setStreamAfterUpload(true)
        setWsKey((k) => k + 1)
      } else {
        setUploadMessage(json.detail || 'Upload failed')
      }
    } catch (err) {
      setUploadMessage('Upload failed: ' + (err.message || 'network error'))
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const statusStyles = {
    Normal:
      'rounded-2xl border border-emerald-500/30 bg-emerald-950/55 px-6 py-6 text-center text-lg font-semibold tracking-tight text-emerald-50 shadow-[inset_0_1px_0_rgba(255,255,255,0.06),0_16px_40px_-12px_rgba(0,0,0,0.5)] ring-1 ring-emerald-400/15 backdrop-blur-sm md:px-8 md:py-7',
    Kick:
      'rounded-2xl border border-red-500/35 bg-red-950/50 px-6 py-6 text-center text-lg font-semibold tracking-tight text-red-50 shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_16px_40px_-12px_rgba(0,0,0,0.55)] ring-1 ring-red-400/20 backdrop-blur-sm md:px-8 md:py-7',
  }
  const statusLabels = {
    Normal: 'Normal',
    Kick: 'KICK DETECTED',
    Loss: 'LOSS DETECTED',
  }

  const liveDotClass =
    wsStatus === 'connected'
      ? 'bg-emerald-400 shadow-[0_0_0_2px_rgba(16,185,129,0.35),0_0_14px_rgba(52,211,153,0.95)]'
      : wsStatus === 'connecting'
        ? 'bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,0.6)] animate-pulse'
        : 'bg-zinc-600 shadow-none'

  return (
    <>
      {alertsOpen && <AlertsCenter onBack={() => setAlertsOpen(false)} />}
      <div
        className={`mx-auto flex w-full max-w-lg flex-col px-5 pb-6 pt-[max(1.5rem,env(safe-area-inset-top))] md:max-w-2xl md:px-8 md:pb-10 ${alertsOpen ? 'hidden' : ''}`}
        aria-hidden={alertsOpen}
      >
        <header className="mb-10 flex items-center justify-between gap-4 md:mb-12">
          <h1 className="text-[1.4rem] font-semibold tracking-tight text-slate-50 md:text-2xl">
            Rig Lab AI
          </h1>
          <button
            type="button"
            aria-label="Alarms and notifications"
            onClick={() => setAlertsOpen(true)}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-white/[0.08] bg-slate-950/50 text-slate-100 shadow-inner shadow-black/20 ring-1 ring-white/[0.06] backdrop-blur-sm transition hover:bg-slate-900/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-violet-400/70"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="currentColor"
              className="h-6 w-6"
              aria-hidden
            >
              <path
                fillRule="evenodd"
                d="M5.25 9a6.75 6.75 0 0 1 13.5 0v.75c0 2.25.75 4.5 2.25 6.75a.75.75 0 0 1-.63 1.14H3.63a.75.75 0 0 1-.63-1.14 15.15 15.15 0 0 0 2.25-6.75V9Zm6.004 9.75a3 3 0 0 0 2.995-2.823h-5.99A3 3 0 0 0 11.254 18.75ZM12 2.25a8.25 8.25 0 0 1 8.25 8.25v.75c0 2.25.75 4.5 2.25 6.75a.75.75 0 0 1-.63 1.14H3.63a.75.75 0 0 1-.63-1.14 15.15 15.15 0 0 0 2.25-6.75V10.5A8.25 8.25 0 0 1 12 2.25Z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </header>

        <nav className="mb-10 md:mb-12" aria-label="Chart metric">
          <p className="mb-3 text-[0.7rem] font-semibold uppercase tracking-[0.14em] text-slate-500">
            Metric
          </p>
          <div
            role="tablist"
            className="-mx-1 flex snap-x snap-mandatory gap-2.5 overflow-x-auto px-1 pb-1 pt-0.5 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden md:gap-3"
          >
            {METRIC_ORDER.map((id) => {
              const active = selectedMetric === id
              const label = METRIC_CONFIG[id].title
              return (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => setSelectedMetric(id)}
                  className={`snap-start whitespace-nowrap rounded-full px-6 py-2.5 text-sm font-semibold tracking-tight transition focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/70 md:px-7 md:py-3 ${
                    active
                      ? 'border border-cyan-300/90 bg-gradient-to-b from-[#22d3ee] to-[#0099e6] text-white shadow-[0_0_0_1px_rgba(56,189,248,0.5),0_4px_20px_rgba(14,165,233,0.45),0_12px_32px_-8px_rgba(0,120,200,0.55)]'
                      : 'border border-white/[0.12] bg-gradient-to-b from-white/[0.14] to-white/[0.04] text-slate-300 shadow-[inset_0_1px_0_rgba(255,255,255,0.14),0_4px_16px_rgba(0,0,0,0.25)] backdrop-blur-xl hover:from-white/[0.18] hover:to-white/[0.07] hover:text-slate-100'
                  }`}
                >
                  {label}
                </button>
              )
            })}
          </div>
        </nav>

        <div className="flex flex-1 flex-col gap-8 md:gap-10">
          {situation === 'Loss' ? (
            <section
              className="relative overflow-hidden rounded-2xl border border-orange-600/45 shadow-[0_22px_50px_-14px_rgba(124,45,18,0.65),inset_0_1px_0_rgba(255,255,255,0.06)] ring-1 ring-orange-500/20"
              aria-live="polite"
            >
              <div
                className="pointer-events-none absolute inset-0 bg-gradient-to-br from-[#431407] via-[#9a3412] to-[#292524]"
                aria-hidden
              />
              <div
                className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_90%_55%_at_50%_-10%,rgba(251,146,60,0.28),transparent_58%)]"
                aria-hidden
              />
              <div
                className="pointer-events-none absolute inset-0 opacity-[0.18] bg-[repeating-linear-gradient(-45deg,rgba(0,0,0,0.22)_0,rgba(0,0,0,0.22)_1px,transparent_1px,transparent_5px)] mix-blend-overlay"
                aria-hidden
              />
              <div
                className="pointer-events-none absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-orange-300/45 to-transparent"
                aria-hidden
              />
              <div className="relative px-6 py-7 text-center md:px-8 md:py-8">
                <p className="animate-loss-text-glow text-lg font-bold tracking-[0.12em] text-orange-50 md:text-xl">
                  {statusLabels.Loss}
                </p>
              </div>
            </section>
          ) : (
            <section
              className={statusStyles[situation] ?? statusStyles.Normal}
              aria-live="polite"
            >
              {statusLabels[situation] ?? 'Normal'}
            </section>
          )}

          <section className="rounded-2xl border border-white/[0.09] bg-slate-950/70 p-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.05),0_24px_48px_-12px_rgba(0,0,0,0.6)] ring-1 ring-white/[0.06] backdrop-blur-md md:p-7">
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls"
              onChange={handleUpload}
              className="hidden"
            />
            <div className="flex flex-col gap-5 sm:flex-row sm:flex-wrap sm:items-center">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="rounded-xl bg-gradient-to-r from-violet-600 via-indigo-600 to-fuchsia-700 px-5 py-3.5 text-sm font-semibold text-white shadow-lg shadow-violet-950/50 transition hover:brightness-110 disabled:opacity-50"
              >
                {uploading ? 'Uploading…' : 'Upload Excel file'}
              </button>
              {uploadMessage && (
                <span className="text-sm font-medium leading-snug text-slate-100">
                  {uploadMessage}
                </span>
              )}
              <div className="flex min-w-0 flex-1 items-center justify-start gap-2.5 sm:justify-end">
                <span
                  className={`h-2.5 w-2.5 shrink-0 rounded-full ${liveDotClass}`}
                  aria-hidden
                />
                <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-100">
                  {wsStatus === 'connected'
                    ? 'Live · Connected'
                    : wsStatus === 'connecting'
                      ? 'Live · Connecting'
                      : 'Live · Disconnected'}
                </span>
              </div>
            </div>
          </section>

          <Charts data={data} metric={selectedMetric} />
        </div>
      </div>
    </>
  )
}

export default Dashboard
