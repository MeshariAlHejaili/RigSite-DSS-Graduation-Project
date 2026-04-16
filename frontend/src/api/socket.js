const MAX_RETRIES = 10
const RETRY_DELAY_MS = 3000

let socket = null
let status = 'DISCONNECTED'
let retries = 0
let reconnectTimer = null
let manualClose = false
let sessionCount = 0
const listeners = new Set()

function emit(payload) {
  listeners.forEach((listener) => listener(payload))
}

function emitMeta() {
  emit({ __meta: true, status, count: sessionCount })
}

function clearReconnectTimer() {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
}

function getSocketUrl() {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${window.location.host}/ws/live`
}

function scheduleReconnect() {
  if (manualClose) {
    return
  }

  if (reconnectTimer) {
    return
  }

  if (retries >= MAX_RETRIES) {
    status = 'FAILED'
    emitMeta()
    return
  }

  status = 'DISCONNECTED'
  retries += 1
  emitMeta()
  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null
    connect()
  }, RETRY_DELAY_MS)
}

function connect() {
  manualClose = false
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) {
    return
  }

  socket = new WebSocket(getSocketUrl())

  socket.onopen = () => {
    clearReconnectTimer()
    retries = 0
    status = 'LIVE'
    emitMeta()
  }

  socket.onmessage = (event) => {
    console.log('RigLab live message:', event.data)
    const payload = JSON.parse(event.data)
    sessionCount += 1
    emit(payload)
    emitMeta()
  }

  socket.onerror = () => {
    scheduleReconnect()
  }

  socket.onclose = () => {
    scheduleReconnect()
  }
}

function disconnect() {
  manualClose = true
  clearReconnectTimer()
  if (socket) {
    socket.onclose = null
    socket.onerror = null
    socket.close()
    socket = null
  }
  status = 'DISCONNECTED'
  emitMeta()
}

function onMessage(callback) {
  listeners.add(callback)
  return () => {
    listeners.delete(callback)
  }
}

function getStatus() {
  return status
}

function getCount() {
  return sessionCount
}

export default { connect, disconnect, onMessage, getStatus, getCount }
