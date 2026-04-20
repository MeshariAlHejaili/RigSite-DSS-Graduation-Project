import { useEffect, useState } from 'react'

const MODE_LABELS = {
  angle_only: 'Angle Only',
  angle_density: 'Angle + Density',
}

const BASELINE_SAMPLES = 3

function getLastAngles(buffer) {
  // Return the last BASELINE_SAMPLES records that have a valid gate_angle
  const valid = buffer.filter((r) => r.gate_angle != null && r.state !== 'SENSOR_FAULT')
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
          setMode(data.detection_mode)
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
    const samples = getLastAngles(buffer)
    if (samples.length < BASELINE_SAMPLES) {
      setSetMsg(`Need ${BASELINE_SAMPLES} valid data points — only ${samples.length} available.`)
      return
    }

    const baselineAngle = average(samples.map((r) => r.gate_angle))

    let baselineDensity = null
    if (mode === 'angle_density') {
      const densities = samples.map((r) => r.density).filter((d) => d != null)
      if (densities.length === BASELINE_SAMPLES) {
        baselineDensity = average(densities)
      }
    }

    setSetting(true)
    setSetMsg('')
    setError('')
    try {
      const response = await fetch('/api/v1/detection-config/set-baseline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ baseline_angle: baselineAngle, baseline_density: baselineDensity }),
      })
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to set baseline')
      }
      setSetMsg(`Baseline set to ${baselineAngle.toFixed(2)}°`)
    } catch (err) {
      setError(err.message)
    } finally {
      setSetting(false)
    }
  }

  function handleGoToSettings() {
    window.location.hash = '/settings'
  }

  const modeLabel = MODE_LABELS[mode] ?? mode
  const canSetBaseline = getLastAngles(buffer).length >= BASELINE_SAMPLES

  return (
    <section className="chart-card detection-summary-card">
      <div className="detection-summary-row">
        <div className="detection-summary-info">
          <span className="detection-summary-heading">Detection Mode</span>
          <span className="detection-summary-value">{modeLabel}</span>
          <span className="detection-summary-sep">|</span>
          <span className="detection-summary-heading">Baseline</span>
          <span className={`detection-summary-value ${currentBaselineAngle == null ? 'detection-summary-no-baseline' : ''}`}>
            {currentBaselineAngle != null ? `${currentBaselineAngle.toFixed(2)}°` : 'Not set'}
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
