import { useEffect, useState } from 'react'

const MODES = [
  { id: 'normal', label: 'Normal' },
  { id: 'kick', label: 'Kick' },
  { id: 'loss', label: 'Loss' },
]

export default function SimulatorControls() {
  const [mode, setMode] = useState('normal')
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    async function loadState() {
      try {
        const response = await fetch('/api/v1/simulator')
        if (!response.ok) {
          throw new Error('Failed to load simulator state')
        }
        const data = await response.json()
        if (active) {
          setMode(data.mode)
          setError('')
        }
      } catch (fetchError) {
        if (active) {
          setError(fetchError.message)
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadState()
    return () => {
      active = false
    }
  }, [])

  async function handleModeChange(nextMode) {
    setUpdating(true)
    setError('')
    try {
      const response = await fetch('/api/v1/simulator', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode: nextMode }),
      })
      if (!response.ok) {
        throw new Error('Failed to update simulator mode')
      }
      const data = await response.json()
      setMode(data.mode)
    } catch (fetchError) {
      setError(fetchError.message)
    } finally {
      setUpdating(false)
    }
  }

  return (
    <section className="chart-card simulator-card">
      <div className="simulator-header">
        <div>
          <h2>Simulator Controls</h2>
          <p className="simulator-description">
            Switch the payload mode. The alarm stays separate and only changes after 5 consecutive qualifying payloads.
          </p>
        </div>
        <div className="simulator-status">
          Active mode: <strong>{loading ? 'Loading...' : mode}</strong>
        </div>
      </div>

      <div className="simulator-actions">
        {MODES.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`simulator-button ${mode === item.id ? 'simulator-button-active' : ''}`}
            disabled={loading || updating}
            onClick={() => handleModeChange(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {error ? <div className="simulator-error">{error}</div> : null}
    </section>
  )
}
