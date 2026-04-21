import { useEffect, useRef, useState } from 'react'

const mode = 'mounted'

function formatMaybeNumber(value, digits = 2) {
  if (value == null || Number.isNaN(Number(value))) return '--'
  return Number(value).toFixed(digits)
}

export default function AngleTestUpload() {
  const fileInputRef = useRef(null)
  const calibFileInputRef = useRef(null)
  const cameraCalibFileInputRef = useRef(null)

  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [pressure1, setPressure1] = useState(5.0)
  const [pressure2, setPressure2] = useState(4.0)
  const [flow, setFlow] = useState(5.0)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState('')
  const [error, setError] = useState('')
  const [calibrated, setCalibrated] = useState(false)
  const [cameraCalibrated, setCameraCalibrated] = useState(false)
  const [calibMsg, setCalibMsg] = useState('')
  const [cameraMsg, setCameraMsg] = useState('')
  const [zeroCalibration, setZeroCalibration] = useState(null)
  const [cameraCalibration, setCameraCalibration] = useState(null)

  useEffect(() => {
    refreshStatus()
  }, [])

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview)
    }
  }, [preview])

  async function refreshStatus() {
    try {
      const response = await fetch('/api/v1/angle/calibrate/status')
      const data = await response.json()
      setCalibrated(Boolean(data.calibrated))
      setZeroCalibration(data.zero_calibration ?? null)
      setCameraCalibration(data.camera_calibration ?? null)
      setCameraCalibrated(Boolean(data.camera_calibration?.calibrated))
    } catch {
      // Leave existing status in place on transient errors.
    }
  }

  function handleFileChange(event) {
    const selected = event.target.files?.[0]
    if (!selected) return
    setFile(selected)
    setResult(null)
    setError('')
    if (preview) URL.revokeObjectURL(preview)
    setPreview(URL.createObjectURL(selected))
  }

  async function handleCalibFileChange(event) {
    const selectedFiles = Array.from(event.target.files ?? [])
    if (selectedFiles.length === 0) return
    setLoading('calib')
    setCalibMsg('')
    setError('')
    try {
      const form = new FormData()
      selectedFiles.forEach((selected) => form.append('images', selected))
      form.append('mode', mode)
      const res = await fetch('/api/v1/angle/calibrate/zero', { method: 'POST', body: form })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()
      setCalibrated(Boolean(data.success))
      setCalibMsg(data.message || '')
      setZeroCalibration(data.calibration ?? null)
      setCameraCalibration(data.camera_calibration ?? null)
      setCameraCalibrated(Boolean(data.camera_calibration?.calibrated))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading('')
      event.target.value = ''
    }
  }

  async function handleCameraCalibrationFileChange(event) {
    const selected = event.target.files?.[0]
    if (!selected) return
    setLoading('camera-calib')
    setCameraMsg('')
    setError('')
    try {
      const form = new FormData()
      form.append('file', selected)
      const res = await fetch('/api/v1/angle/camera-calibration/upload', { method: 'POST', body: form })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()
      setCameraMsg(data.message || '')
      setCameraCalibration(data.camera_calibration ?? null)
      setCameraCalibrated(Boolean(data.camera_calibration?.calibrated))
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading('')
      event.target.value = ''
    }
  }

  async function handleClearCalib() {
    setLoading('clear')
    setError('')
    try {
      const res = await fetch('/api/v1/angle/calibrate/zero', { method: 'DELETE' })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()
      setCalibrated(false)
      setCalibMsg(data.message || 'Calibration cleared.')
      setZeroCalibration(data.zero_calibration ?? null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading('')
    }
  }

  async function handleClearCameraCalibration() {
    setLoading('clear-camera-calib')
    setError('')
    try {
      const res = await fetch('/api/v1/angle/camera-calibration', { method: 'DELETE' })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()
      setCameraMsg(data.message || 'Camera calibration cleared.')
      setCameraCalibration(data.camera_calibration ?? null)
      setCameraCalibrated(false)
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
      form.append('mode', mode)
      const res = await fetch('/api/v1/angle/detect', { method: 'POST', body: form })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()
      setCalibrated(Boolean(data.calibrated))
      setZeroCalibration(data.zero_calibration ?? zeroCalibration)
      setCameraCalibration(data.camera_calibration ?? cameraCalibration)
      setCameraCalibrated(Boolean(data.camera_calibration?.calibrated))
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
      form.append('mode', mode)
      const res = await fetch('/api/v1/angle/ingest', { method: 'POST', body: form })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json()
      setCalibrated(Boolean(data.calibrated))
      setZeroCalibration(data.zero_calibration ?? zeroCalibration)
      setCameraCalibration(data.camera_calibration ?? cameraCalibration)
      setCameraCalibrated(Boolean(data.camera_calibration?.calibrated))
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
          <h2>Gate Angle Photo Test</h2>
          <p className="angle-upload-desc">
            Test the backend ArUco detector with manual images. Uses the mounted camera production path for reliable
            fixed-viewpoint angle detection.
          </p>
        </div>
        <div className="angle-status-stack">
          <span className={`angle-calib-badge ${calibrated ? 'angle-calib-ok' : 'angle-calib-warn'}`}>
            {calibrated ? 'Zero Calibrated' : 'Zero Not Set'}
          </span>
          <span className={`angle-calib-badge ${cameraCalibrated ? 'angle-calib-ok' : 'angle-calib-warn'}`}>
            {cameraCalibrated ? 'Camera Calibrated' : 'Using Fallback Intrinsics'}
          </span>
        </div>
      </div>

      <div className="angle-calib-panel">
        <div className="angle-calib-block">
          <h3>Zero Calibration</h3>
          <p className="angle-calib-panel-text">
            Upload 3-5 images of the closed gate for a more stable zero reference. Single-image calibration still works
            as a fallback.
          </p>
          <div className="angle-calib-row">
            <input
              type="file"
              accept="image/*"
              multiple
              ref={calibFileInputRef}
              style={{ display: 'none' }}
              onChange={handleCalibFileChange}
            />
            <button
              type="button"
              className={`simulator-button ${calibrated ? '' : 'angle-calib-cta'}`}
              disabled={loading !== ''}
              onClick={() => calibFileInputRef.current?.click()}
            >
              {loading === 'calib' ? 'Calibrating...' : calibrated ? 'Re-calibrate Zero' : 'Calibrate Zero'}
            </button>
            {calibrated && (
              <button
                type="button"
                className="angle-clear-btn"
                disabled={loading !== ''}
                onClick={handleClearCalib}
              >
                {loading === 'clear' ? '...' : 'Clear'}
              </button>
            )}
            {calibMsg && <span className="angle-calib-msg">{calibMsg}</span>}
          </div>
          {zeroCalibration?.configured && (
            <p className="angle-calib-panel-meta">
              Samples: {zeroCalibration.samples_used ?? '--'} | Mean reprojection error:{' '}
              {formatMaybeNumber(zeroCalibration.mean_reprojection_error, 3)} px
            </p>
          )}
        </div>

        <div className="angle-calib-block">
          <h3>Camera Calibration</h3>
          <p className="angle-calib-panel-text">
            Upload a JSON calibration file with <code>camera_matrix</code> and <code>dist_coeffs</code> to replace the
            fallback camera model.
          </p>
          <div className="angle-calib-row">
            <input
              type="file"
              accept=".json,application/json"
              ref={cameraCalibFileInputRef}
              style={{ display: 'none' }}
              onChange={handleCameraCalibrationFileChange}
            />
            <button
              type="button"
              className={`simulator-button ${cameraCalibrated ? '' : 'angle-calib-cta'}`}
              disabled={loading !== ''}
              onClick={() => cameraCalibFileInputRef.current?.click()}
            >
              {loading === 'camera-calib' ? 'Uploading...' : cameraCalibrated ? 'Replace Camera Calibration' : 'Upload Camera Calibration'}
            </button>
            {cameraCalibration?.configured && (
              <button
                type="button"
                className="angle-clear-btn"
                disabled={loading !== ''}
                onClick={handleClearCameraCalibration}
              >
                {loading === 'clear-camera-calib' ? '...' : 'Clear'}
              </button>
            )}
            {cameraMsg && <span className="angle-calib-msg">{cameraMsg}</span>}
          </div>
          <p className="angle-calib-panel-meta">
            Source: {cameraCalibration?.source ?? 'synthetic'} | Profile:{' '}
            {cameraCalibration?.image_size
              ? `${cameraCalibration.image_size.width}x${cameraCalibration.image_size.height}`
              : 'not provided'}
          </p>
        </div>
      </div>

      {!cameraCalibrated && (
        <p className="angle-calib-hint">
          Real camera calibration is not loaded yet. The detector can still run, but pose stability will be weaker
          because it must fall back to synthetic intrinsics.
        </p>
      )}

      <div className="angle-upload-row">
        <input
          type="file"
          accept="image/*"
          ref={fileInputRef}
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />
        <button type="button" className="simulator-button" onClick={() => fileInputRef.current?.click()}>
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
                onChange={(event) => setPressure1(parseFloat(event.target.value))}
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
                onChange={(event) => setPressure2(parseFloat(event.target.value))}
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
                onChange={(event) => setFlow(parseFloat(event.target.value))}
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
              {loading === 'detect' ? 'Detecting...' : 'Detect Angle Only'}
            </button>
            <button
              type="button"
              className="simulator-button simulator-button-active"
              disabled={loading !== ''}
              onClick={handleIngest}
            >
              {loading === 'ingest' ? 'Ingesting...' : 'Ingest Full Frame'}
            </button>
          </div>
        </>
      )}

      {error && <div className="simulator-error">{error}</div>}

      {result && (
        <div className="angle-result">
          {result.detected === false ? (
            <span className="angle-result-none">{result.warning || 'No reliable ArUco marker pose detected in this photo.'}</span>
          ) : (
            <>
              <div className="angle-result-row">
                <span className="angle-result-label">Gate Angle</span>
                <span className="angle-result-value">{result.gate_angle?.toFixed(1)}°</span>
              </div>
              <div className="angle-result-row">
                <span className="angle-result-label">Confidence</span>
                <span className="angle-result-value">{formatMaybeNumber(result.confidence, 3)}</span>
              </div>
              <div className="angle-result-row">
                <span className="angle-result-label">Mode</span>
                <span className="angle-result-value">{result.mode}</span>
              </div>
              <div className="angle-result-row">
                <span className="angle-result-label">Viewpoint Consistent</span>
                <span className="angle-result-value">
                  {result.viewpoint_consistent == null ? '--' : result.viewpoint_consistent ? 'Yes' : 'No'}
                </span>
              </div>
              <div className="angle-result-row">
                <span className="angle-result-label">Reprojection Error</span>
                <span className="angle-result-value">{formatMaybeNumber(result.reprojection_error, 3)} px</span>
              </div>
              {result.mode === 'ingest' && (
                <div className="angle-result-row">
                  <span className="angle-result-label">Pipeline State</span>
                  <span className="angle-result-value">{result.state}</span>
                </div>
              )}
              {result.warning && <p className="angle-result-warning">{result.warning}</p>}
            </>
          )}
        </div>
      )}
    </section>
  )
}
