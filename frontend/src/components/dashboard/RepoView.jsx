import { useMemo, useState } from 'react'
import Plot from 'react-plotly.js'
import { useNavigate, useParams } from 'react-router-dom'

const MOCK_MODULES = [
  { id: 'auth', name: 'auth', risk: 0.72, coverage: 88 },
  { id: 'billing', name: 'billing', risk: 0.63, coverage: 81 },
  { id: 'checkout', name: 'checkout', risk: 0.84, coverage: 76 },
  { id: 'notifications', name: 'notifications', risk: 0.39, coverage: 92 },
]

const MOCK_COVERAGE_TREND = [
  { date: '2025-11-01', coverage: 78 },
  { date: '2025-11-08', coverage: 80 },
  { date: '2025-11-15', coverage: 82 },
  { date: '2025-11-22', coverage: 83 },
  { date: '2025-11-29', coverage: 85 },
]

export function RepoView() {
  const navigate = useNavigate()
  const { id: repoId } = useParams()

  const [dateFrom, setDateFrom] = useState('2025-11-01')
  const [dateTo, setDateTo] = useState('2025-11-30')
  const [riskThreshold, setRiskThreshold] = useState(0.5)
  const [selectedModuleId, setSelectedModuleId] = useState('all')

  const filteredModules = useMemo(
    () =>
      MOCK_MODULES.filter(
        (m) => m.risk >= riskThreshold && (selectedModuleId === 'all' || m.id === selectedModuleId),
      ),
    [riskThreshold, selectedModuleId],
  )

  const moduleHeatmapData = useMemo(() => {
    const labels = MOCK_MODULES.map((m) => m.name)
    const riskValues = MOCK_MODULES.map((m) => m.risk)
    return { labels, riskValues }
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">
            Repository
          </p>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-50">
            Repo {repoId}
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            Deep dive into module-level risk and test coverage for this repository.
          </p>
        </div>
      </div>

      {/* Filters */}
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3 shadow-sm">
        <div className="flex flex-wrap gap-4 items-end text-xs">
          <div className="flex flex-col gap-1">
            <label className="text-slate-400">Date from</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100 text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-slate-400">Date to</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100 text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-slate-400">
              Risk threshold ({riskThreshold.toFixed(2)})
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={riskThreshold}
              onChange={(e) => setRiskThreshold(Number(e.target.value))}
              className="accent-primary-500"
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-slate-400">Module</label>
            <select
              value={selectedModuleId}
              onChange={(e) => setSelectedModuleId(e.target.value)}
              className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-slate-100 text-xs focus:outline-none focus:ring-1 focus:ring-primary-500"
            >
              <option value="all">All modules</option>
              {MOCK_MODULES.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Charts */}
      <section className="grid gap-6 lg:grid-cols-5 items-start">
        {/* Coverage trend */}
        <div className="lg:col-span-3 rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
          <header className="mb-4">
            <h2 className="text-sm font-semibold text-slate-100">
              Coverage trend
            </h2>
            <p className="text-xs text-slate-500">
              Line chart of coverage over the selected date range.
            </p>
          </header>
          <div className="h-64">
            <Plot
              data={[
                {
                  type: 'scatter',
                  mode: 'lines+markers',
                  x: MOCK_COVERAGE_TREND.map((p) => p.date),
                  y: MOCK_COVERAGE_TREND.map((p) => p.coverage),
                  line: { color: '#4f46e5', width: 2 },
                  marker: { color: '#a5b4fc' },
                },
              ]}
              layout={{
                autosize: true,
                paper_bgcolor: 'rgba(15,23,42,0)',
                plot_bgcolor: 'rgba(15,23,42,0)',
                margin: { l: 50, r: 16, t: 10, b: 40 },
                xaxis: {
                  tickfont: { color: '#9ca3af', size: 11 },
                },
                yaxis: {
                  tickfont: { color: '#9ca3af', size: 11 },
                  gridcolor: '#1f2933',
                  zerolinecolor: '#1f2933',
                  title: { text: 'Coverage (%)', font: { color: '#9ca3af', size: 11 } },
                },
                showlegend: false,
              }}
              config={{ displaylogo: false, responsive: true }}
              style={{ width: '100%', height: '100%' }}
              useResizeHandler
            />
          </div>
        </div>

        {/* Module risk heatmap */}
        <div className="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
          <header className="mb-4">
            <h2 className="text-sm font-semibold text-slate-100">
              Module risk heatmap
            </h2>
            <p className="text-xs text-slate-500">
              Relative risk per module (darker = riskier).
            </p>
          </header>
          <div className="h-64">
            <Plot
              data={[
                {
                  type: 'heatmap',
                  z: [moduleHeatmapData.riskValues],
                  x: moduleHeatmapData.labels,
                  y: ['Risk'],
                  colorscale: [
                    [0, '#22c55e'],
                    [0.5, '#eab308'],
                    [1, '#f97373'],
                  ],
                },
              ]}
              layout={{
                autosize: true,
                paper_bgcolor: 'rgba(15,23,42,0)',
                plot_bgcolor: 'rgba(15,23,42,0)',
                margin: { l: 40, r: 16, t: 10, b: 40 },
                xaxis: {
                  tickfont: { color: '#9ca3af', size: 11 },
                },
                yaxis: {
                  tickfont: { color: '#9ca3af', size: 11 },
                },
                showlegend: false,
              }}
              config={{ displaylogo: false, responsive: true }}
              style={{ width: '100%', height: '100%' }}
              useResizeHandler
            />
          </div>
        </div>
      </section>

      {/* Modules table with drill-down */}
      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
        <header className="mb-3">
          <h2 className="text-sm font-semibold text-slate-100">
            Modules (filtered)
          </h2>
          <p className="text-xs text-slate-500">
            Click a module row to drill down to its detailed view.
          </p>
        </header>
        <div className="overflow-hidden border border-slate-800 rounded-lg">
          <table className="w-full text-xs">
            <thead className="bg-slate-900 text-slate-400">
              <tr>
                <th className="px-3 py-2 text-left font-medium">Module</th>
                <th className="px-3 py-2 text-right font-medium">Risk</th>
                <th className="px-3 py-2 text-right font-medium">Coverage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-950">
              {filteredModules.map((module) => (
                <tr
                  key={module.id}
                  className="cursor-pointer hover:bg-slate-900/70"
                  onClick={() => navigate(`/module/${encodeURIComponent(module.id)}`)}
                >
                  <td className="px-3 py-2 text-slate-100">{module.name}</td>
                  <td className="px-3 py-2 text-right font-semibold text-amber-300">
                    {module.risk.toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-right text-slate-100">
                    {module.coverage}%
                  </td>
                </tr>
              ))}
              {filteredModules.length === 0 && (
                <tr>
                  <td
                    colSpan={3}
                    className="px-3 py-6 text-center text-slate-500"
                  >
                    No modules match the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}


