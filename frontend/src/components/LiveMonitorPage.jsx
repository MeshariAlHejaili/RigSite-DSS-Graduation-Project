import AngleChart from './AngleChart.jsx'
import DataTable from './DataTable.jsx'
import DetectionSummary from './DetectionSummary.jsx'
import FlowChart from './FlowChart.jsx'
import MudWeightChart from './MudWeightChart.jsx'
// TODO: Remove PiCameraFeed component after testing
import PiCameraFeed from './PiCameraFeed.jsx'
import PressureChart from './PressureChart.jsx'
import StateBadge from './StateBadge.jsx'
import ViscosityChart from './ViscosityChart.jsx'

export default function LiveMonitorPage({
  buffer,
  latestRecord,
  previewRows,
  showDebugStatus,
}) {
  return (
    <>
      <StateBadge data={latestRecord} showDebugStatus={showDebugStatus} />

      <section className="charts-row">
        <FlowChart data={buffer} />
        <PressureChart data={buffer} />
      </section>

      <section className="charts-row">
        <MudWeightChart data={buffer} />
        <ViscosityChart data={buffer} />
      </section>

      <AngleChart data={buffer} />
      <DetectionSummary buffer={buffer} />
      <section className="chart-card">
        <h2>Pi Camera Feed (Testing)</h2>
        <PiCameraFeed />
      </section>
      <DataTable
        data={previewRows}
        title="Quick Raw Data Preview"
        subtitle="Showing the latest 20 records. Open History / Raw Data for full triage view."
        emptyMessage="No records to preview yet."
      />
    </>
  )
}
