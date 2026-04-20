import { useEffect, useState } from 'react'

const MODES = [
  {
    id: 'angle_only',
    label: 'Angle Only',
    description: 'Detects kick/loss based on gate angle deviation from baseline (±5°).',
  },
  {
    id: 'angle_density',
    label: 'Angle + Density',
    description:
      'Detects kick/loss based on gate angle deviation (±5°) OR mud density deviation (±10%) from baseline. Requires Δh to calculate density.',
  },
]

export default function SettingsPage() {
  const [mode, setMode] = useState('angle_only')
  const [deltaH, setDeltaH] = useState(1.0)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    async function loadSettings() {
      try {
        const response = await fetch('/api/v1/detection-config')
        if (!response.ok) throw new Error('Failed to load detection settings')
        const data = await response.json()
        if (active) {
          setMode(data.detection_mode)
          setDeltaH(data.delta_h)
          setError('')
        }
      } catch (err) {
        if (active) setError(err.message)
      } finally {
        if (active) setLoading(false)
      }
    }

    loadSettings()
    return () => {
      active = false
    }
  }, [])

  async function handleSave() {
    setSaving(true)
    setSaveStatus('')
    setError('')

    const body = { detection_mode: mode }
    if (mode === 'angle_density') {
      body.delta_h = parseFloat(deltaH) || 1.0
    }

    try {
      const response = await fetch('/api/v1/detection-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Failed to save settings')
      }
      const data = await response.json()
      setMode(data.detection_mode)
      setDeltaH(data.delta_h)
      setSaveStatus('Settings saved.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <section className="chart-card settings-section">
        <h2>Detection Settings</h2>
        <p className="settings-hint">Loading...</p>
      </section>
    )
  }

  return (
    <div className="settings-page">
      <section className="chart-card settings-section">
        <h2>Detection Mode</h2>
        <p className="settings-hint">
          Choose how the system identifies kick and loss events. The baseline is established from
          the first 3 data points after a session starts (or after a mode change).
        </p>

        <div className="settings-mode-grid">
          {MODES.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`settings-mode-card ${mode === item.id ? 'settings-mode-card-active' : ''}`}
              onClick={() => {
                setMode(item.id)
                setSaveStatus('')
              }}
            >
              <span className="settings-mode-title">{item.label}</span>
              <span className="settings-mode-desc">{item.description}</span>
            </button>
          ))}
        </div>

        {mode === 'angle_density' && (
          <div className="settings-field">
            <label className="settings-label" htmlFor="delta-h-input">
              Δh — Height difference between pressure sensors (meters)
            </label>
            <p className="settings-field-hint">
              This is the vertical distance between the two pressure measurement points on the rig.
              It changes from rig to rig and rarely needs updating during normal operation.
            </p>
            <input
              id="delta-h-input"
              type="number"
              className="settings-input"
              value={deltaH}
              min="0.1"
              step="0.1"
              onChange={(e) => {
                setDeltaH(e.target.value)
                setSaveStatus('')
              }}
            />
            <span className="settings-input-unit">m</span>
          </div>
        )}

        <div className="settings-actions">
          <button
            type="button"
            className="report-button"
            disabled={saving}
            onClick={handleSave}
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          {saveStatus && <span className="settings-save-ok">{saveStatus}</span>}
          {error && <span className="settings-error">{error}</span>}
        </div>
      </section>

      <section className="chart-card settings-section">
        <h2>Detection Logic Reference</h2>
        <p className="settings-hint">How detection works in each mode.</p>

        <div className="settings-reference">
          <div className="settings-ref-block">
            <h3>Angle Only</h3>
            <ul>
              <li>Baseline: average gate angle over the first 3 data points.</li>
              <li>
                <strong>Kick:</strong> angle {'>'} baseline + 5° for 3 consecutive points.
              </li>
              <li>
                <strong>Loss:</strong> angle {'<'} baseline − 5° for 3 consecutive points.
              </li>
            </ul>
          </div>
          <div className="settings-ref-block">
            <h3>Angle + Density</h3>
            <ul>
              <li>Baseline: average angle and average density over the first 3 data points.</li>
              <li>
                Density formula: <code>ρ = ΔP / (g × Δh)</code> (ΔP in PSI → converted to Pa; Δh in meters → ρ in kg/m³)
              </li>
              <li>
                <strong>Kick:</strong> (angle {'>'} baseline + 5°) <em>OR</em> (density {'>'} baseline density × 1.10) for 3 consecutive points.
              </li>
              <li>
                <strong>Loss:</strong> (angle {'<'} baseline − 5°) <em>OR</em> (density {'<'} baseline density × 0.90) for 3 consecutive points.
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  )
}
