import { useCallback, useEffect, useRef, useState } from 'react'

export default function AngleTestUpload() {
  const fileInputRef = useRef(null)
  const calibFileInputRef = useRef(null)

  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [pressure1, setPressure1] = useState(5.0)
  const [pressure2, setPressure2] = useState(4.0)
  const [flow, setFlow] = useState(5.0)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState('')
  const [error, setError] = useState('')
  const [calibrated, setCalibrated] = useState(false)
  const [calibMsg, setCalibMsg] = useState('')

  // Poll calibration status on mount
  useEffect(() => {
    fetch('/api/v1/angle/calibrate/status')
      .then((r) => r.json())
      .then((d) => setCalibrated(d.calibrated))
      .catch(() => {})
  }, [])

  function handleFileChange(e) {
    const selected = e.target.files?.[0]
    if (!selected) return
    setFile(selected)
    setResult(null)
    setError('')
    if (preview) URL.revokeObjectURL(preview)
    setPreview(URL.createObjectURL(selected))
  }

  const handleCalibFileChange = useCallback(async (e) => {
    const selected = e.target.files?.[0]
    if (!selected) return
    setLoading('calib')
    setCalibMsg('')
    setError('')
    try {
      const form = new FormData()
      form.append('image', selected)
      const res = await fetch('/api/v1/angle/calibrate/zero', { method: 'POST', body: form })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()
      setCalibrated(data.success)
      setCalibMsg(data.message)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading('')
      // Reset input so the same file can be re-uploaded if needed
      e.target.value = ''
    }
  }, [preview])

  async function handleClearCalib() {
    setLoading('clear')
    try {
      await fetch('/api/v1/angle/calibrate/zero', { method: 'DELETE' })
      setCalibrated(false)
      setCalibMsg('Calibration cleared.')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading('')
    }
  }

  async function handleDetect() {
    if (!file) return
    setLoading('detect')
    setError('')
    setResult(null)
    try {
      const form = new FormData()
      form.append('image', file)
      const res = await fetch('/api/v1/angle/detect', { method: 'POST', body: form })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()
      setCalibrated(data.calibrated)
      setResult({ mode: 'detect', ...data })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading('')
    }
  }

  async function handleIngest() {
    if (!file) return
    setLoading('ingest')
    setError('')
    setResult(null)
    try {
      const form = new FormData()
      form.append('image', file)
      form.append('pressure1', String(pressure1))
      form.append('pressure2', String(pressure2))
      form.append('flow', String(flow))
      const res = await fetch('/api/v1/angle/ingest', { method: 'POST', body: form })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()
      setCalibrated(data.calibrated)
      setResult({ mode: 'ingest', ...data })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading('')
    }
  }

  return (
    <section className="chart-card angle-upload-card">
      <div className="angle-upload-header">
        <div>
          <h2>Gate Angle — Photo Test</h2>
          <p className="angle-upload-desc">
            Upload a photo containing the ArUco marker to test detection.
          </p>
        </div>
        <span className={`angle-calib-badge ${calibrated ? 'angle-calib-ok' : 'angle-calib-warn'}`}>
          {calibrated ? 'Calibrated' : 'Not calibrated'}
        </span>
      </div>

      {/* ── Calibration row ─────────────────────────────────────── */}
      <div className="angle-calib-row">
        <input
          type="file"
          accept="image/*"
          ref={calibFileInputRef}
          style={{ display: 'none' }}
          onChange={handleCalibFileChange}
        />
        <button
          type="button"
          className={`simulator-button ${calibrated ? '' : 'angle-calib-cta'}`}
          disabled={loading !== ''}
          onClick={() => calibFileInputRef.current?.click()}
          title="Upload a photo of the gate fully closed to set the 0° reference"
        >
          {loading === 'calib' ? 'Calibrating…' : calibrated ? 'Re-calibrate Zero' : 'Calibrate Zero (Close Gate First)'}
        </button>
        {calibrated && (
          <button
            type="button"
            className="angle-clear-btn"
            disabled={loading !== ''}
            onClick={handleClearCalib}
          >
            {loading === 'clear' ? '…' : 'Clear'}
          </button>
        )}
        {calibMsg && <span className="angle-calib-msg">{calibMsg}</span>}
      </div>

      {!calibrated && (
        <p className="angle-calib-hint">
          Angles shown below are raw (not zeroed). Calibrate first for accurate readings.
        </p>
      )}

      {/* ── Photo upload ─────────────────────────────────────────── */}
      <div className="angle-upload-row">
        <input
          type="file"
          accept="image/*"
          ref={fileInputRef}
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        <button
          type="button"
          className="simulator-button"
          onClick={() => fileInputRef.current?.click()}
        >
          {file ? 'Change Photo' : 'Choose Photo'}
        </button>
        {file && <span className="angle-upload-filename">{file.name}</span>}
      </div>

      {preview && (
        <div className="angle-preview-wrap">
          <img className="angle-preview-img" src={preview} alt="Selected gate photo" />
        </div>
      )}

      {file && (
        <>
          <div className="angle-sensor-row">
            <label className="angle-sensor-label">
              P1 (PSI)
              <input
                className="angle-sensor-input"
                type="number"
                step="0.1"
                min="0"
                max="20"
                value={pressure1}
                onChange={(e) => setPressure1(parseFloat(e.target.value))}
              />
            </label>
            <label className="angle-sensor-label">
              P2 (PSI)
              <input
                className="angle-sensor-input"
                type="number"
                step="0.1"
                min="0"
                max="20"
                value={pressure2}
                onChange={(e) => setPressure2(parseFloat(e.target.value))}
              />
            </label>
            <label className="angle-sensor-label">
              Flow (L/min)
              <input
                className="angle-sensor-input"
                type="number"
                step="0.1"
                min="0"
                max="30"
                value={flow}
                onChange={(e) => setFlow(parseFloat(e.target.value))}
              />
            </label>
          </div>

          <div className="angle-upload-actions">
            <button
              type="button"
              className="simulator-button"
              disabled={loading !== ''}
              onClick={handleDetect}
            >
              {loading === 'detect' ? 'Detecting…' : 'Detect Angle Only'}
            </button>
            <button
              type="button"
              className="simulator-button simulator-button-active"
              disabled={loading !== ''}
              onClick={handleIngest}
            >
              {loading === 'ingest' ? 'Ingesting…' : 'Ingest Full Frame'}
            </button>
          </div>
        </>
      )}

      {error && <div className="simulator-error">{error}</div>}

      {result && (
        <div className="angle-result">
          {result.detected === false ? (
            <span className="angle-result-none">No ArUco marker detected in this photo.</span>
          ) : (
            <>
              <div className="angle-result-row">
                <span className="angle-result-label">Gate Angle</span>
                <span className="angle-result-value">{result.gate_angle?.toFixed(1)}°</span>
              </div>
              <div className="angle-result-row">
                <span className="angle-result-label">Confidence</span>
                <span className="angle-result-value">
                  {((result.angle_confidence ?? 0) * 100).toFixed(1)}%
                </span>
              </div>
              {result.mode === 'ingest' && (
                <div className="angle-result-row">
                  <span className="angle-result-label">Pipeline State</span>
                  <span className="angle-result-value">{result.state}</span>
                </div>
              )}
              {!result.calibrated && (
                <p className="angle-calib-hint" style={{ marginTop: 8 }}>
                  Raw angle (uncalibrated) — calibrate zero for accurate readings.
                </p>
              )}
            </>
          )}
        </div>
      )}
    </section>
  )
}
