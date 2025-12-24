import { useParams, Link } from 'react-router-dom'
import { TrendLineChart } from '../components/charts/TrendLineChart'

export function ClassPage() {
  const { id } = useParams()

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">
            Class
          </p>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-50">
            Class #{id}
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
            Repo
          </Link>
          <span className="text-slate-600">/</span>
          <Link
            to="/module/1"
            className="text-primary-400 hover:text-primary-300 underline underline-offset-4"
          >
            Module
          </Link>
        </div>
      </div>

      <TrendLineChart title="Class-level defects" />
    </div>
  )
}


