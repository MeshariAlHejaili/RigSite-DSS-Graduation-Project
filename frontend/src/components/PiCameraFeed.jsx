import { useEffect, useState } from 'react'

const FEED_STYLE = {
  display: 'flex',
  flexDirection: 'column',
  gap: '12px',
}

const STATUS_STYLE = {
  margin: 0,
  color: '#475569',
  fontSize: '0.9rem',
}

const EMPTY_STYLE = {
  border: '1px dashed #cbd5e1',
  borderRadius: '14px',
  padding: '28px 16px',
  background: '#f8fafc',
  color: '#64748b',
  textAlign: 'center',
  fontSize: '0.92rem',
  fontWeight: 600,
}

const IMAGE_STYLE = {
  display: 'block',
  width: '100%',
  maxHeight: '420px',
  borderRadius: '14px',
  border: '1px solid rgba(148, 163, 184, 0.28)',
  background: '#f8fafc',
  objectFit: 'contain',
}

export default function PiCameraFeed() {
  const [imageSrc, setImageSrc] = useState('')
  const [available, setAvailable] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true

    async function loadLatestImage() {
      try {
        const response = await fetch('/api/v1/pi/latest-image')
        if (!response.ok) {
          throw new Error('Failed to load Pi camera feed')
        }

        const data = await response.json()
        if (!active) return

        const hasImage = Boolean(data.available && data.image_b64)
        setAvailable(hasImage)
        setImageSrc(hasImage ? `data:image/jpeg;base64,${data.image_b64}` : '')
        setError('')
      } catch (fetchError) {
        if (!active) return
        setError(fetchError.message)
      }
    }

    loadLatestImage()
    const intervalId = window.setInterval(loadLatestImage, 1000)

    return () => {
      active = false
      window.clearInterval(intervalId)
    }
  }, [])

  return (
    <div style={FEED_STYLE}>
      <p style={STATUS_STYLE}>Polling the latest image from the Raspberry Pi every second.</p>

      {error ? <div className="simulator-error">{error}</div> : null}

      {available && imageSrc ? (
        <img
          src={imageSrc}
          alt="Latest Raspberry Pi camera frame"
          style={IMAGE_STYLE}
        />
      ) : (
        <div style={EMPTY_STYLE}>No image yet</div>
      )}
    </div>
  )
}
