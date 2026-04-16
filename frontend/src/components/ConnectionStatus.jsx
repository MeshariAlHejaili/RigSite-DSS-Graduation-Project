export default function ConnectionStatus({ status, count }) {
  const isLive = status === 'LIVE'
  const label = isLive
    ? 'LIVE'
    : status === 'FAILED'
      ? 'FAILED'
      : 'DISCONNECTED - Reconnecting...'

  return (
    <div className="connection-status">
      <span className={`status-dot ${isLive ? 'status-dot-live' : 'status-dot-dead'}`} />
      <span className="connection-label">{label}</span>
      <span className="connection-count">{count} records this session</span>
    </div>
  )
}
