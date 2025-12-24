import { useCallback, useState } from 'react'
import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'

/**
 * Hook for exporting prioritisation plans to CSV and PDF.
 *
 * @param {Object} options
 * @param {{ key: string; label: string }[]} options.planColumns
 * @param {Array<Record<string, any>>} options.planRows
 * @param {{ label: string; value: string | number }[]} options.riskMetrics
 * @param {{ classId: string; name: string; risk: number; coverage?: number }[]} options.topRiskyClasses
 * @param {string} [options.coverageChartElementId] - DOM id of a Plotly chart div for PNG export
 * @param {string} [options.fileBaseName='quality-dashboard-report'] - base file name without extension
 */
export function useExport(options) {
  const {
    planColumns,
    planRows,
    riskMetrics,
    topRiskyClasses,
    coverageChartElementId,
    fileBaseName = 'quality-dashboard-report',
  } = options

  const [isExportingCSV, setIsExportingCSV] = useState(false)
  const [isExportingPDF, setIsExportingPDF] = useState(false)

  const exportCSV = useCallback(() => {
    if (!planColumns?.length) return
    setIsExportingCSV(true)

    try {
      const header = planColumns.map((c) => c.label)
      const rows = (planRows ?? []).map((row) =>
        planColumns.map((c) => toCell(row[c.key])),
      )

      const csvLines = [header, ...rows]
        .map((line) =>
          line
            .map((cell) => {
              const v = String(cell ?? '')
              if (v.includes(',') || v.includes('"') || v.includes('\n')) {
                return `"${v.replace(/"/g, '""')}"`
              }
              return v
            })
            .join(','),
        )
        .join('\n')

      const blob = new Blob([csvLines], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `${fileBaseName}.csv`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
    } finally {
      setIsExportingCSV(false)
    }
  }, [fileBaseName, planColumns, planRows])

  const exportPDF = useCallback(async () => {
    setIsExportingPDF(true)
    try {
      const doc = new jsPDF({
        orientation: 'p',
        unit: 'pt',
        format: 'a4',
      })

      const marginLeft = 48
      let cursorY = 48

      // Title
      doc.setFont('helvetica', 'bold')
      doc.setFontSize(16)
      doc.text('Quality Dashboard – Prioritisation Report', marginLeft, cursorY)
      cursorY += 18

      doc.setFont('helvetica', 'normal')
      doc.setFontSize(10)
      doc.setTextColor(120)
      doc.text(
        `Generated: ${new Date().toLocaleString()}`,
        marginLeft,
        cursorY,
      )
      cursorY += 24

      // Risk metrics summary
      if (riskMetrics?.length) {
        doc.setTextColor(0)
        doc.setFontSize(12)
        doc.setFont('helvetica', 'bold')
        doc.text('Risk metrics', marginLeft, cursorY)
        cursorY += 12

        doc.setFont('helvetica', 'normal')
        doc.setFontSize(10)
        cursorY += 4
        riskMetrics.forEach((m) => {
          doc.text(
            `${m.label}: ${String(m.value)}`,
            marginLeft,
            cursorY,
          )
          cursorY += 12
        })
        cursorY += 8
      }

      // Top risky classes table
      if (topRiskyClasses?.length) {
        autoTable(doc, {
          startY: cursorY,
          head: [['Class', 'Risk', 'Coverage']],
          body: topRiskyClasses.map((c) => [
            `${c.name} (${c.classId})`,
            c.risk.toFixed(2),
            c.coverage != null ? `${c.coverage}%` : '—',
          ]),
          styles: { fontSize: 9 },
          headStyles: { fillColor: [15, 23, 42] },
        })
        cursorY = doc.lastAutoTable.finalY + 16
      }

      // Coverage chart as PNG
      if (coverageChartElementId && window.Plotly) {
        const chartElement = document.getElementById(coverageChartElementId)
        if (chartElement) {
          try {
            const dataUrl = await window.Plotly.toImage(chartElement, {
              format: 'png',
              width: 600,
              height: 260,
            })
            if (doc.internal.pageSize.getHeight() - cursorY < 280) {
              doc.addPage()
              cursorY = 48
            }
            doc.setFont('helvetica', 'bold')
            doc.setFontSize(12)
            doc.text('Coverage trend', marginLeft, cursorY)
            cursorY += 12

            doc.addImage(
              dataUrl,
              'PNG',
              marginLeft,
              cursorY,
              600,
              260,
            )
            cursorY += 276
          } catch {
            // ignore chart export errors and continue
          }
        }
      }

      // Prioritisation plan table
      if (planColumns?.length && planRows?.length) {
        autoTable(doc, {
          startY: cursorY,
          head: [planColumns.map((c) => c.label)],
          body: planRows.map((row) =>
            planColumns.map((c) => toCell(row[c.key])),
          ),
          styles: { fontSize: 8 },
          headStyles: { fillColor: [15, 23, 42] },
        })
      }

      doc.save(`${fileBaseName}.pdf`)
    } finally {
      setIsExportingPDF(false)
    }
  }, [
    coverageChartElementId,
    fileBaseName,
    planColumns,
    planRows,
    riskMetrics,
    topRiskyClasses,
  ])

  return {
    exportCSV,
    exportPDF,
    isExportingCSV,
    isExportingPDF,
  }
}

function toCell(value) {
  if (value == null) return ''
  if (typeof value === 'number') return value
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  return String(value)
}


