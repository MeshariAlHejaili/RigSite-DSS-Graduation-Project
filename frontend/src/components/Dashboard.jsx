import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import Charts from './Charts'

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
    Normal: 'bg-emerald-600 border-emerald-400 text-white',
    Kick: 'bg-red-600 border-red-400 text-white',
    Loss: 'bg-orange-500 border-orange-300 text-white',
  }
  const statusLabels = {
    Normal: 'Normal',
    Kick: 'KICK DETECTED',
    Loss: 'LOSS DETECTED',
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-slate-100">RigLab-AI Monitor</h1>
      </header>

      <div
        className={`mb-6 rounded-lg border-2 p-6 text-center text-xl font-semibold ${statusStyles[situation] ?? statusStyles.Normal}`}
      >
        {statusLabels[situation] ?? 'Normal'}
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls"
          onChange={handleUpload}
          className="hidden"
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          className="rounded-lg bg-slate-600 px-4 py-2 font-medium text-white hover:bg-slate-500 disabled:opacity-50"
        >
          {uploading ? 'Uploading…' : 'Upload Excel file'}
        </button>
        {uploadMessage && (
          <span className="text-sm text-slate-300">{uploadMessage}</span>
        )}
        <span className="text-sm text-slate-400">
          WebSocket: {wsStatus}
        </span>
      </div>

      <Charts data={data} />
    </div>
  )
}

export default Dashboard
