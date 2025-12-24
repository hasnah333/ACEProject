import { useExport } from '../../hooks/useExport'

/**
 * Button to generate a PDF report using jsPDF + autoTable.
 *
 * Props mirror the `useExport` options:
 * - planColumns
 * - planRows
 * - riskMetrics
 * - topRiskyClasses
 * - coverageChartElementId?
 * - fileBaseName?
 */
export function ExportPDF(props) {
  const { exportPDF, isExportingPDF } = useExport(props)

  return (
    <button
      type="button"
      onClick={exportPDF}
      disabled={isExportingPDF}
      className="inline-flex items-center gap-1 rounded-md border border-primary-600 bg-primary-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-70"
    >
      {isExportingPDF ? 'Generating…' : 'Export PDF'}
    </button>
  )
}


