import AngleTestUpload from './AngleTestUpload.jsx'
import SimulatorControls from './SimulatorControls.jsx'

export default function SimulationPage() {
  return (
    <>
      <section className="chart-card simulation-hero">
        <h2>Simulation</h2>
        <p className="simulation-description">
          Upload gate angle images for manual detection testing, and control the telemetry simulator
          to verify system response under different well-event scenarios.
        </p>
      </section>
      <AngleTestUpload />
      <SimulatorControls />
    </>
  )
}
