import { useEffect, useState } from 'react'

import socket from './api/socket.js'
import AngleChart from './components/AngleChart.jsx'
import ConnectionStatus from './components/ConnectionStatus.jsx'
import DataTable from './components/DataTable.jsx'
import FlowChart from './components/FlowChart.jsx'
import PressureChart from './components/PressureChart.jsx'
import ReportControls from './components/ReportControls.jsx'
import SimulatorControls from './components/SimulatorControls.jsx'
import StateBadge from './components/StateBadge.jsx'

const BUFFER_SIZE = 60

export default function App() {
  const [buffer, setBuffer] = useState([])
  const [status, setStatus] = useState(socket.getStatus())
  const [sessionCount, setSessionCount] = useState(socket.getCount())

  useEffect(() => {
    const unsubscribe = socket.onMessage((message) => {
      if (message.__meta) {
        setStatus(message.status)
        setSessionCount(message.count)
        return
      }

      setBuffer((current) => {
        const next = [...current, message]
        return next.length > BUFFER_SIZE ? next.slice(next.length - BUFFER_SIZE) : next
      })
    })

    socket.connect()
    return () => {
      unsubscribe()
      socket.disconnect()
    }
  }, [])

  const latestRecord = buffer[buffer.length - 1] ?? null
  const lastTwentyRecords = buffer.slice(-20).reverse()

  return (
    <>
      <header className="app-header">
        <div className="brand-block">
          <h1>RigLab-AI Monitor</h1>
          <p>Live mud return line telemetry</p>
        </div>
        <ConnectionStatus status={status} count={sessionCount} />
      </header>

      <main className="app-main">
        <StateBadge data={latestRecord} />

        <section className="charts-row">
          <FlowChart data={buffer} />
          <PressureChart data={buffer} />
        </section>

        <AngleChart data={buffer} />
        <DataTable data={lastTwentyRecords} />
        <ReportControls />
        <SimulatorControls />
      </main>
    </>
  )
}
