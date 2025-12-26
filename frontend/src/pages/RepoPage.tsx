import { useParams, Link } from 'react-router-dom'
import { TrendLineChart } from '../components/charts/TrendLineChart'
import { ModuleQualityTable } from '../components/tables/ModuleQualityTable'
import { useRepos } from '../context/RepoContext'

export function RepoPage() {
  const { id } = useParams()
  const { getRepo } = useRepos()
  const repo = getRepo(id)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">
            Repository
          </p>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
            {repo ? repo.name : `Repo ${id}`}
          </h1>
          {repo && (
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              {repo.url} · branch {repo.defaultBranch}
            </p>
          )}
        </div>
        <div className="flex gap-4 text-xs">
          <Link
            to="/"
            className="text-primary-500 hover:text-primary-400 underline underline-offset-4"
          >
            Overview
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
        <div className="xl:col-span-2">
          <TrendLineChart title="Coverage by module" repoId={id} />
        </div>
        <div className="xl:col-span-1">
          <ModuleQualityTable repoId={id} />
        </div>
      </div>
    </div>
  )
}
