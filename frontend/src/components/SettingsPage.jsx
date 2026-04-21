import { useEffect, useMemo, useState } from 'react'

const DISPLAY_OPTIONS = [
  {
    value: 'normal',
    label: 'Normal Mud Weight',
    description: 'Use clean mud weight as the primary display value (ppg).',
  },
  {
    value: 'cuttings',
    label: 'Mud Weight w/ Cuttings',
    description: 'Use cuttings-adjusted mud weight as the primary display value (ppg).',
  },
]

const DETECTION_OPTIONS = [
  {
    value: 'angle_only',
    label: 'Angle Only',
    description: 'Classify kick/loss using gate-angle deviation only.',
  },
  {
    value: 'angle_mud_weight',
    label: 'Angle + Mud Weight',
    description: 'Classify kick/loss using angle OR mud-weight deviation thresholds.',
  },
]

const BASELINE_SAMPLES = 3

function normalizeDetectionMode(mode) {
  if (mode === 'angle_density') return 'angle_mud_weight'
  if (mode === 'angle_only' || mode === 'angle_mud_weight') return mode
  return 'angle_only'
}

function formatBaselineValue(value, unit) {
  if (value == null) return '--'
  return `${Number(value).toFixed(2)} ${unit}`
}

export default function SettingsPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const [displayMudWeight, setDisplayMudWeight] = useState('normal')
  const [showMudWeightColumns, setShowMudWeightColumns] = useState(true)
  const [detectionMode, setDetectionMode] = useState('angle_only')
  const [baselineAngle, setBaselineAngle] = useState(null)
  const [baselineMudWeight, setBaselineMudWeight] = useState(null)

  const [cuttingsDensity, setCuttingsDensity] = useState('21.0')
  const [cuttingsVolumeFraction, setCuttingsVolumeFraction] = useState('0.08')
  const [suspensionFactor, setSuspensionFactor] = useState('1.00')
  const [deltaH, setDeltaH] = useState('1.0')

  const [fieldErrors, setFieldErrors] = useState({})
  const [statusMessage, setStatusMessage] = useState('')
  const [statusType, setStatusType] = useState('')

  useEffect(() => {
    let active = true

    async function loadSettings() {
      setLoading(true)
      setStatusMessage('')
      setStatusType('')
      try {
        const [runtimeResponse, detectionResponse] = await Promise.all([
          fetch('/api/v1/config'),
          fetch('/api/v1/detection-config'),
        ])

        if (!runtimeResponse.ok) {
          throw new Error('Failed to load runtime settings.')
        }
        if (!detectionResponse.ok) {
          throw new Error('Failed to load detection settings.')
        }

        const runtimeData = await runtimeResponse.json()
        const detectionData = await detectionResponse.json()

        if (!active) return

        setDisplayMudWeight(runtimeData.display_mud_weight === 'cuttings' ? 'cuttings' : 'normal')
        setCuttingsDensity(String(runtimeData.cuttings_density ?? '21.0'))
        setCuttingsVolumeFraction(String(runtimeData.cuttings_volume_fraction ?? '0.08'))
        setSuspensionFactor(String(runtimeData.suspension_factor ?? '1.00'))
        setDeltaH(String(runtimeData.delta_h_ft ?? detectionData.delta_h_ft ?? '1.0'))

        setDetectionMode(normalizeDetectionMode(detectionData.detection_mode))
        setBaselineAngle(detectionData.baseline_angle ?? null)
        setBaselineMudWeight(detectionData.baseline_mud_weight ?? null)

        setFieldErrors({})
      } catch (error) {
        if (active) {
          setStatusMessage(error.message || 'Failed to load settings.')
          setStatusType('error')
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadSettings()
    return () => {
      active = false
    }
  }, [])

  function validateFields() {
    const errors = {}

    const cuttingsDensityValue = parseFloat(cuttingsDensity)
    const cuttingsVolumeFractionValue = parseFloat(cuttingsVolumeFraction)
    const suspensionFactorValue = parseFloat(suspensionFactor)
    const deltaHValue = parseFloat(deltaH)

    if (Number.isNaN(cuttingsDensityValue) || cuttingsDensityValue <= 0) {
      errors.cuttings_density = 'Cuttings density must be a positive number.'
    }

    if (
      Number.isNaN(cuttingsVolumeFractionValue) ||
      cuttingsVolumeFractionValue < 0 ||
      cuttingsVolumeFractionValue > 1
    ) {
      errors.cuttings_volume_fraction = 'Cuttings volume fraction must be between 0.00 and 1.00.'
    }

    if (Number.isNaN(suspensionFactorValue) || suspensionFactorValue <= 0) {
      errors.suspension_factor = 'Suspension factor must be greater than 0.'
    }

    if (Number.isNaN(deltaHValue) || deltaHValue <= 0) {
      errors.delta_h_ft = 'Delta h must be greater than 0.'
    }

    return errors
  }

  function handleApplySettings() {
    if (loading || saving) {
      return
    }

    const errors = validateFields()
    setFieldErrors(errors)

    if (Object.keys(errors).length > 0) {
      setStatusMessage('Please fix validation errors before applying settings.')
      setStatusType('error')
      return
    }

    const runtimePayload = {
      display_mud_weight: displayMudWeight,
      delta_h_ft: parseFloat(deltaH),
      cuttings_density: parseFloat(cuttingsDensity),
      cuttings_volume_fraction: parseFloat(cuttingsVolumeFraction),
      suspension_factor: parseFloat(suspensionFactor),
    }

    const detectionPayload = {
      detection_mode: normalizeDetectionMode(detectionMode),
    }

    async function saveAll() {
      setSaving(true)
      setStatusMessage('')
      setStatusType('')
      try {
        const [runtimeResponse, detectionResponse] = await Promise.all([
          fetch('/api/v1/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(runtimePayload),
          }),
          fetch('/api/v1/detection-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(detectionPayload),
          }),
        ])

        if (!runtimeResponse.ok) {
          const payload = await runtimeResponse.json().catch(() => ({}))
          throw new Error(payload.detail || 'Failed to save runtime settings.')
        }

        if (!detectionResponse.ok) {
          const payload = await detectionResponse.json().catch(() => ({}))
          throw new Error(payload.detail || 'Failed to save detection settings.')
        }

        const [runtimeData, detectionData] = await Promise.all([
          runtimeResponse.json(),
          detectionResponse.json(),
        ])
        setDetectionMode(normalizeDetectionMode(detectionData.detection_mode))
        setDeltaH(String(runtimeData.delta_h_ft ?? detectionData.delta_h_ft ?? deltaH))
        setBaselineAngle(detectionData.baseline_angle ?? null)
        setBaselineMudWeight(detectionData.baseline_mud_weight ?? null)
        setStatusMessage(`Settings applied at ${new Date().toLocaleTimeString()}.`)
        setStatusType('ok')
      } catch (error) {
        setStatusMessage(error.message || 'Failed to apply settings.')
        setStatusType('error')
      } finally {
        setSaving(false)
      }
    }

    saveAll()
  }

  const detectionReadiness = useMemo(() => {
    if (normalizeDetectionMode(detectionMode) === 'angle_mud_weight') {
      if (baselineAngle != null && baselineMudWeight != null) {
        return {
          ready: true,
          text: 'Ready for Angle + Mud Weight detection.',
        }
      }
      return {
        ready: false,
        text: `Manual baseline required (set from latest ${BASELINE_SAMPLES} points).`,
      }
    }

    if (baselineAngle != null) {
      return {
        ready: true,
        text: 'Ready for Angle Only detection.',
      }
    }

    return {
      ready: false,
      text: `Manual baseline required (set from latest ${BASELINE_SAMPLES} points).`,
    }
  }, [baselineAngle, baselineMudWeight, detectionMode])

  return (
    <div className="settings-page">
      <section className="chart-card settings-section">
        <h2>Detection Strategy</h2>
        <p className="settings-hint">
          Choose the active detection mode and confirm baseline readiness before live triage.
        </p>

        <div className="settings-mode-grid">
          {DETECTION_OPTIONS.map((option) => (
            <label
              key={option.value}
              className={`settings-mode-card ${
                normalizeDetectionMode(detectionMode) === option.value ? 'settings-mode-card-active' : ''
              }`}
            >
              <input
                type="radio"
                name="detection_mode"
                value={option.value}
                checked={normalizeDetectionMode(detectionMode) === option.value}
                onChange={(event) => setDetectionMode(normalizeDetectionMode(event.target.value))}
              />
              <span className="settings-mode-title">{option.label}</span>
              <span className="settings-mode-desc">{option.description}</span>
            </label>
          ))}
        </div>

        <p className={detectionReadiness.ready ? 'settings-save-ok' : 'settings-error'}>{detectionReadiness.text}</p>
        <p className="settings-hint">
          Baseline angle: {formatBaselineValue(baselineAngle, 'deg')} | Baseline mud weight:{' '}
          {formatBaselineValue(baselineMudWeight, 'ppg')}
        </p>
      </section>

      <section className="chart-card settings-section">
        <h2>Mud Weight Display Preferences</h2>
        <p className="settings-hint">
          Select which mud-weight signal is displayed and used for angle + mud-weight detection.
        </p>

        <div className="settings-option-group">
          {DISPLAY_OPTIONS.map((option) => (
            <label key={option.value} className="settings-option">
              <input
                type="radio"
                name="display_mud_weight"
                value={option.value}
                checked={displayMudWeight === option.value}
                onChange={(event) => setDisplayMudWeight(event.target.value)}
              />
              <span>
                <strong>{option.label}</strong>
                <small>{option.description}</small>
              </span>
            </label>
          ))}
        </div>

        <label className="settings-checkbox">
          <input
            type="checkbox"
            checked={showMudWeightColumns}
            onChange={(event) => setShowMudWeightColumns(event.target.checked)}
          />
          <span>Show mud weight columns in History / Raw Data table</span>
        </label>
      </section>

      <section className="chart-card settings-section">
        <h2>PETE Engineering Inputs</h2>
        <p className="settings-hint">
          Inputs required by petroleum engineers for mud-weight calculations. Mud weight uses MW = dP / (0.052 * delta_h).
        </p>

        <div className="settings-form-grid">
          <div className="settings-field">
            <label className="settings-label" htmlFor="delta-h-input">
              delta_h
            </label>
            <p className="settings-field-hint">Vertical height difference used as delta_h in MW = dP / (0.052 * delta_h).</p>
            <input
              id="delta-h-input"
              type="number"
              className="settings-input"
              value={deltaH}
              step="0.1"
              min="0.001"
              onChange={(event) => setDeltaH(event.target.value)}
            />
            <span className="settings-input-unit">ft</span>
            {fieldErrors.delta_h_ft && <span className="settings-error">{fieldErrors.delta_h_ft}</span>}
          </div>

          <div className="settings-field">
            <label className="settings-label" htmlFor="cuttings-density-input">
              cuttings_density
            </label>
            <p className="settings-field-hint">Cuttings density in pounds per gallon.</p>
            <input
              id="cuttings-density-input"
              type="number"
              className="settings-input"
              value={cuttingsDensity}
              step="0.1"
              min="0"
              onChange={(event) => setCuttingsDensity(event.target.value)}
            />
            <span className="settings-input-unit">ppg</span>
            {fieldErrors.cuttings_density && <span className="settings-error">{fieldErrors.cuttings_density}</span>}
          </div>

          <div className="settings-field">
            <label className="settings-label" htmlFor="cuttings-volume-fraction-input">
              cuttings_volume_fraction
            </label>
            <p className="settings-field-hint">Fraction of cuttings volume in the mud mixture (0.00 to 1.00).</p>
            <input
              id="cuttings-volume-fraction-input"
              type="number"
              className="settings-input"
              value={cuttingsVolumeFraction}
              step="0.01"
              min="0"
              max="1"
              onChange={(event) => setCuttingsVolumeFraction(event.target.value)}
            />
            <span className="settings-input-unit">fraction</span>
            {fieldErrors.cuttings_volume_fraction && (
              <span className="settings-error">{fieldErrors.cuttings_volume_fraction}</span>
            )}
          </div>

          <div className="settings-field">
            <label className="settings-label" htmlFor="suspension-factor-input">
              suspension_factor
            </label>
            <p className="settings-field-hint">Dimensionless suspension and size-effect factor.</p>
            <input
              id="suspension-factor-input"
              type="number"
              className="settings-input"
              value={suspensionFactor}
              step="0.01"
              min="0"
              onChange={(event) => setSuspensionFactor(event.target.value)}
            />
            <span className="settings-input-unit">unitless</span>
            {fieldErrors.suspension_factor && <span className="settings-error">{fieldErrors.suspension_factor}</span>}
          </div>
        </div>

        <div className="settings-actions">
          <button type="button" className="report-button" onClick={handleApplySettings} disabled={loading || saving}>
            {loading ? 'Loading...' : saving ? 'Applying...' : 'Apply Settings'}
          </button>
          {statusMessage && (
            <span className={statusType === 'error' ? 'settings-error' : 'settings-save-ok'}>
              {statusMessage}
            </span>
          )}
        </div>
      </section>
    </div>
  )
}
