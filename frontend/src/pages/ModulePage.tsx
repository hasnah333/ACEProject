import { useParams, Link } from 'react-router-dom'
import { TrendLineChart } from '../components/charts/TrendLineChart'
import { ClassQualityTable } from '../components/tables/ClassQualityTable'

export function ModulePage() {
  const { id } = useParams()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">
            Module
          </p>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-50">
            Module #{id}
          </h1>
        </div>
        <div className="flex gap-4 text-xs">
          <Link
            to="/"
            className="text-primary-400 hover:text-primary-300 underline underline-offset-4"
          >
            Overview
          </Link>
          <span className="text-slate-600">/</span>
          <Link
            to="/repo/1"
            className="text-primary-400 hover:text-primary-300 underline underline-offset-4"
          >
            Parent repo
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
        <div className="xl:col-span-2">
          <TrendLineChart title="Flakiness over time" />
        </div>
        <div className="xl:col-span-1">
          <ClassQualityTable />
        </div>
      </div>
    </div>
  )
}


