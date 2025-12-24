import Plot from 'react-plotly.js'
import { Link } from 'react-router-dom'

const summaryStats = {
  totalCommits: '12,483',
  globalRiskScore: 0.34,
  coverageTrend: '+4.2% last 30 days',
}

const riskBuckets = [
  { label: 'Low', value: 42 },
  { label: 'Medium', value: 27 },
  { label: 'High', value: 9 },
]

const topRiskyFiles = [
  {
    id: '1',
    repoId: 'web-app',
    repoName: 'web-app',
    path: 'src/components/CheckoutForm.tsx',
    riskScore: 0.91,
  },
  {
    id: '2',
    repoId: 'api-service',
    repoName: 'api-service',
    path: 'src/services/BillingService.ts',
    riskScore: 0.87,
  },
  {
    id: '3',
    repoId: 'web-app',
    repoName: 'web-app',
    path: 'src/hooks/useCart.ts',
    riskScore: 0.83,
  },
  {
    id: '4',
    repoId: 'worker-jobs',
    repoName: 'worker-jobs',
    path: 'jobs/invoiceReconciliationJob.ts',
    riskScore: 0.81,
  },
  {
    id: '5',
    repoId: 'api-service',
    repoName: 'api-service',
    path: 'src/controllers/InvoiceController.ts',
    riskScore: 0.8,
  },
  {
    id: '6',
    repoId: 'web-app',
    repoName: 'web-app',
    path: 'src/pages/CheckoutPage.tsx',
    riskScore: 0.79,
  },
  {
    id: '7',
    repoId: 'web-app',
    repoName: 'web-app',
    path: 'src/components/PaymentSelector.tsx',
    riskScore: 0.78,
  },
  {
    id: '8',
    repoId: 'api-service',
    repoName: 'api-service',
    path: 'src/services/PaymentGateway.ts',
    riskScore: 0.77,
  },
  {
    id: '9',
    repoId: 'worker-jobs',
    repoName: 'worker-jobs',
    path: 'jobs/paymentRetryJob.ts',
    riskScore: 0.76,
  },
  {
    id: '10',
    repoId: 'web-app',
    repoName: 'web-app',
    path: 'src/components/OrderSummary.tsx',
    riskScore: 0.75,
  },
]

export function HomeDashboard() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
            Home dashboard
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            High-level view of global risk and the top 10 risky files across your
            repositories.
          </p>
        </div>
      </div>

      {/* Summary cards */}
      <section className="grid gap-4 sm:grid-cols-3">
        <article className="rounded-xl border border-slate-200/70 bg-white/80 px-4 py-3 shadow-sm transition-all duration-200 hover:-translate-y-[1px] hover:shadow-md hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900/70 dark:hover:border-slate-700">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Total commits
          </p>
          <p className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-50">
            {summaryStats.totalCommits}
          </p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Across all tracked repositories
          </p>
        </article>

        <article className="rounded-xl border border-slate-200/70 bg-white/80 px-4 py-3 shadow-sm transition-all duration-200 hover:-translate-y-[1px] hover:shadow-md hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900/70 dark:hover:border-slate-700">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Global risk score
          </p>
          <p className="mt-2 text-2xl font-semibold text-amber-300">
            {summaryStats.globalRiskScore.toFixed(2)}
          </p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            0 (safe) → 1 (high risk) aggregated across files
          </p>
        </article>

        <article className="rounded-xl border border-slate-200/70 bg-white/80 px-4 py-3 shadow-sm transition-all duration-200 hover:-translate-y-[1px] hover:shadow-md hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900/70 dark:hover:border-slate-700">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Coverage trend
          </p>
          <p className="mt-2 text-2xl font-semibold text-emerald-300">
            {summaryStats.coverageTrend}
          </p>
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
            Versus previous 30-day window
          </p>
        </article>
      </section>

      {/* Chart + table layout */}
      <section className="grid gap-6 lg:grid-cols-5 items-start">
        {/* Risk distribution chart */}
        <div className="lg:col-span-2 rounded-xl border border-slate-200/70 bg-white/80 p-4 shadow-sm transition-all duration-200 hover:-translate-y-[1px] hover:shadow-md hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900/70 dark:hover:border-slate-700">
          <header className="mb-4 flex items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Risk distribution
              </h2>
              <p className="text-xs text-slate-600 dark:text-slate-500">
                Count of files by risk bucket
              </p>
            </div>
          </header>
          <div className="h-60">
            <Plot
              data={[
                {
                  type: 'bar',
                  x: riskBuckets.map((b) => b.label),
                  y: riskBuckets.map((b) => b.value),
                  marker: {
                    color: ['#22c55e', '#eab308', '#f97373'],
                  },
                },
              ]}
              layout={{
                autosize: true,
                paper_bgcolor: 'rgba(248,250,252,0)',
                plot_bgcolor: 'rgba(248,250,252,0)',
                margin: { l: 40, r: 10, t: 10, b: 40 },
                xaxis: {
                  tickfont: { color: '#9ca3af', size: 11 },
                },
                yaxis: {
                  tickfont: { color: '#9ca3af', size: 11 },
                  gridcolor: '#1f2933',
                  zerolinecolor: '#1f2933',
                },
                showlegend: false,
              }}
              config={{
                displaylogo: false,
                responsive: true,
              }}
              style={{ width: '100%', height: '100%' }}
              useResizeHandler
            />
          </div>
        </div>

        {/* Top risky files table */}
        <div className="lg:col-span-3 rounded-xl border border-slate-200/70 bg-white/80 p-4 shadow-sm transition-all duration-200 hover:-translate-y-[1px] hover:shadow-md hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900/70 dark:hover:border-slate-700">
          <header className="mb-3 flex items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Top 10 risky files
              </h2>
              <p className="text-xs text-slate-600 dark:text-slate-500">
                Files with the highest predicted failure / defect risk
              </p>
            </div>
          </header>
          <div className="overflow-hidden border border-slate-200/70 rounded-lg dark:border-slate-800">
            <table className="w-full text-xs">
              <thead className="bg-slate-100 text-slate-500 dark:bg-slate-900 dark:text-slate-400">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">File</th>
                  <th className="px-3 py-2 text-left font-medium">Repository</th>
                  <th className="px-3 py-2 text-right font-medium">Risk score</th>
                  <th className="px-3 py-2 text-right font-medium">Repo view</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white dark:divide-slate-800 dark:bg-slate-950">
                {topRiskyFiles.map((file) => (
                  <tr key={file.id} className="transition-colors duration-150 hover:bg-slate-50 dark:hover:bg-slate-900">
                    <td className="px-3 py-2 text-slate-900 dark:text-slate-100">
                      <div className="max-w-xs truncate" title={file.path}>
                        {file.path}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-slate-600 dark:text-slate-200">
                      {file.repoName}
                    </td>
                    <td className="px-3 py-2 text-right font-semibold text-amber-300">
                      {file.riskScore.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 text-right">
                      <Link
                        to={`/repo/${encodeURIComponent(file.repoId)}`}
                        className="text-primary-400 hover:text-primary-300 underline underline-offset-2"
                      >
                        Open repo
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  )
}


