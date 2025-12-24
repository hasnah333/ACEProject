import { QualitySummaryCards } from '../components/cards/QualitySummaryCards'
import { TrendLineChart } from '../components/charts/TrendLineChart'
import { RepoQualityTable } from '../components/tables/RepoQualityTable'
import { QualityFilterBar } from '../components/filters/QualityFilterBar'
import { UiCard } from '../components/ui/UiCard'
import { ChartPanel } from '../components/ui/ChartPanel'
import MLflowRuns from '../components/dashboard/MLflowRuns'

export function HomePage() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
          Repository quality overview
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          High-level quality signals across all tracked repositories.
        </p>
      </div>

      <UiCard>
        <QualityFilterBar />
      </UiCard>

      <UiCard>
        <QualitySummaryCards />
      </UiCard>

      <div className="grid items-start gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <ChartPanel
            title="Tests passing over time"
            subtitle="Rolling trend of test pass rate across all repositories."
          >
            <TrendLineChart title="Tests passing over time" />
          </ChartPanel>
        </div>
        <div className="lg:col-span-2">
          <UiCard>
            <RepoQualityTable />
          </UiCard>
        </div>
      </div>

      <UiCard>
        <MLflowRuns />
      </UiCard>
    </div>
  )
}


