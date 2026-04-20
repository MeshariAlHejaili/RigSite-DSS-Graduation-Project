import { useEffect, useState } from 'react'

const MODE_LABELS = {
  angle_only: 'Angle Only',
  angle_mud_weight: 'Angle + Mud Weight',
  angle_density: 'Angle + Mud Weight',
}

const BASELINE_SAMPLES = 3

function normalizeDetectionMode(mode) {
  if (mode === 'angle_density') return 'angle_mud_weight'
  if (mode === 'angle_only' || mode === 'angle_mud_weight') return mode
  return 'angle_only'
}

function getLastBaselineSamples(buffer, mode) {
  const normalizedMode = normalizeDetectionMode(mode)
  const valid = buffer.filter((row) => {
    if (row.gate_angle == null || row.state === 'SENSOR_FAULT') {
      return false
    }
    if (normalizedMode === 'angle_mud_weight' && row.mud_weight == null) {
      return false
    }
    return true
  })
  return valid.slice(-BASELINE_SAMPLES)
}

function average(values) {
  if (values.length === 0) return null
  return values.reduce((sum, v) => sum + v, 0) / values.length
}

export default function DetectionSummary({ buffer = [] }) {
  const [mode, setMode] = useState('angle_only')
  const [error, setError] = useState('')
  const [setting, setSetting] = useState(false)
  const [setMsg, setSetMsg] = useState('')

  useEffect(() => {
    let active = true

    async function loadSettings() {
      try {
        const response = await fetch('/api/v1/detection-config')
        if (!response.ok) throw new Error('Failed to load')
        const data = await response.json()
        if (active) {
          setMode(normalizeDetectionMode(data.detection_mode))
          setError('')
        }
      } catch (err) {
        if (active) setError(err.message)
      }
    }

    loadSettings()
    return () => {
      active = false
    }
  }, [])

  // Read baseline_angle from the latest broadcast record — kept current automatically
  const latestRecord = buffer[buffer.length - 1] ?? null
  const currentBaselineAngle = latestRecord?.baseline_angle ?? null

  async function handleSetBaseline() {
    const normalizedMode = normalizeDetectionMode(mode)
    const samples = getLastBaselineSamples(buffer, normalizedMode)
    if (samples.length < BASELINE_SAMPLES) {
      setSetMsg(`Need ${BASELINE_SAMPLES} valid data points - only ${samples.length} available.`)
      return
    }

    const baselineAngle = average(samples.map((r) => r.gate_angle))

    let baselineMudWeight = null
    if (normalizedMode === 'angle_mud_weight') {
      const mudWeights = samples.map((record) => record.mud_weight)
      baselineMudWeight = average(mudWeights)
    }

    setSetting(true)
    setSetMsg('')
    setError('')
    try {
      const response = await fetch('/api/v1/detection-config/set-baseline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          baseline_angle: baselineAngle,
          baseline_mud_weight: baselineMudWeight,
        }),
      })
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to set baseline')
      }
      setSetMsg(`Baseline set to ${baselineAngle.toFixed(2)} deg`)
    } catch (err) {
      setError(err.message)
    } finally {
      setSetting(false)
    }
  }

  function handleGoToSettings() {
    window.location.hash = '/settings'
  }

  const normalizedMode = normalizeDetectionMode(mode)
  const modeLabel = MODE_LABELS[normalizedMode] ?? normalizedMode
  const canSetBaseline = getLastBaselineSamples(buffer, normalizedMode).length >= BASELINE_SAMPLES

  return (
    <section className="chart-card detection-summary-card">
      <div className="detection-summary-row">
        <div className="detection-summary-info">
          <span className="detection-summary-heading">Detection Mode</span>
          <span className="detection-summary-value">{modeLabel}</span>
          <span className="detection-summary-sep">|</span>
          <span className="detection-summary-heading">Baseline</span>
          <span className={`detection-summary-value ${currentBaselineAngle == null ? 'detection-summary-no-baseline' : ''}`}>
            {currentBaselineAngle != null ? `${currentBaselineAngle.toFixed(2)} deg` : 'Not set'}
          </span>
        </div>

        <div className="detection-summary-actions">
          <button
            type="button"
            className="detection-summary-set-btn"
            disabled={setting || !canSetBaseline}
            title={
              !canSetBaseline
                ? `Need ${BASELINE_SAMPLES} valid data points to set baseline`
                : `Set baseline from last ${BASELINE_SAMPLES} data points`
            }
            onClick={handleSetBaseline}
          >
            {setting ? 'Setting...' : 'Set Baseline'}
          </button>
          <button
            type="button"
            className="detection-summary-link"
            onClick={handleGoToSettings}
          >
            Settings
          </button>
        </div>
      </div>

      {setMsg && <p className="detection-summary-msg detection-summary-ok">{setMsg}</p>}
      {error && <p className="detection-summary-msg detection-summary-err">{error}</p>}
    </section>
  )
}
