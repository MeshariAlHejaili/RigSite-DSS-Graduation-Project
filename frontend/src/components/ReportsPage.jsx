import ReportControls from './ReportControls.jsx'

export default function ReportsPage() {
  return (
    <>
      <section className="chart-card reports-page-hero">
        <h2>Reports</h2>
        <p className="report-description">
          Generate incident and daily PDFs from a dedicated workspace without crowding the live monitor.
        </p>
      </section>
      <ReportControls />
    </>
  )
}
