import { useState } from 'react'

async function downloadReport(endpoint, filename) {
  const response = await fetch(endpoint, { method: 'POST' })
  if (!response.ok) {
    throw new Error(`Failed to generate ${filename}`)
  }

  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export default function ReportControls() {
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState('')

  async function handleDownload(type) {
    const config = type === 'incident'
      ? { endpoint: '/api/v1/reports/incident', filename: 'incident_report.pdf', label: 'incident report' }
      : { endpoint: '/api/v1/reports/daily', filename: 'daily_summary.pdf', label: 'daily report' }

    setLoading(type)
    setStatus('')
    try {
      await downloadReport(config.endpoint, config.filename)
      setStatus(`Downloaded ${config.label}.`)
    } catch (error) {
      setStatus(error.message)
    } finally {
      setLoading('')
    }
  }

  const isError = status && !status.startsWith('Downloaded')

  return (
    <section className="chart-card report-card">
      <div className="report-header">
        <p className="report-description">
          Generate the incident snapshot for the latest kick/loss incident episode or the current local-day summary.
        </p>
      </div>

      <div className="report-actions">
        <button
          type="button"
          className="report-button"
          disabled={loading !== ''}
          onClick={() => handleDownload('incident')}
        >
          {loading === 'incident' ? 'Generating Incident Report...' : 'Download Incident Report'}
        </button>
        <button
          type="button"
          className="report-button"
          disabled={loading !== ''}
          onClick={() => handleDownload('daily')}
        >
          {loading === 'daily' ? 'Generating Daily Report...' : 'Download Daily Report'}
        </button>
      </div>

      {status ? (
        <div className={`feedback-panel ${isError ? 'feedback-panel-error' : 'feedback-panel-ok'}`}>
          {status}
        </div>
      ) : null}
    </section>
  )
}
