import AngleChart from './AngleChart.jsx'
import AngleTestUpload from './AngleTestUpload.jsx'
import DataTable from './DataTable.jsx'
import DetectionSummary from './DetectionSummary.jsx'
import FlowChart from './FlowChart.jsx'
import PressureChart from './PressureChart.jsx'
import SimulatorControls from './SimulatorControls.jsx'
import StateBadge from './StateBadge.jsx'

export default function LiveMonitorPage({
  buffer,
  latestRecord,
  previewRows,
  showDebugStatus,
  onToggleDebugStatus,
}) {
  return (
    <>
      <section className="chart-card live-toolbar">
        <div className="live-toolbar-row">
          <h2>Live Monitor</h2>
          <label className="debug-toggle">
            <input
              type="checkbox"
              checked={showDebugStatus}
              onChange={(event) => onToggleDebugStatus(event.target.checked)}
            />
            <span>Debug / Raw Status</span>
          </label>
        </div>
      </section>

      <StateBadge data={latestRecord} showDebugStatus={showDebugStatus} />

      <section className="charts-row">
        <FlowChart data={buffer} />
        <PressureChart data={buffer} />
      </section>

      <AngleChart data={buffer} />
      <DetectionSummary buffer={buffer} />
      <AngleTestUpload />
      <SimulatorControls />
      <DataTable
        data={previewRows}
        title="Quick Raw Data Preview"
        subtitle="Showing the latest 20 records. Open History / Raw Data for full triage view."
        emptyMessage="No records to preview yet."
      />
    </>
  )
}
