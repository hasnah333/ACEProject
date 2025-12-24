import { useExport } from '../../hooks/useExport'

/**
 * Button to export a prioritisation plan table as CSV.
 *
 * Props mirror the `useExport` options:
 * - planColumns
 * - planRows
 * - fileBaseName?
 */
export function ExportCSV(props) {
  const { exportCSV, isExportingCSV } = useExport(props)

  return (
    <button
      type="button"
      onClick={exportCSV}
      disabled={isExportingCSV}
      className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-100 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
    >
      {isExportingCSV ? 'Exporting…' : 'Export CSV'}
    </button>
  )
}


