import { NavLink, Outlet } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { ThemeToggle } from '../components/ui/ThemeToggle'
import testscopeLogo from '../assets/testscope-logo.svg'
import { useRepos } from '../context/RepoContext'
import { analyseStatiqueClient } from '../services/api/client'

type QualitySummary = {
  file_count: number
  avg_cyclomatic_complexity: number
  total_code_smells: number
}

function QualityOverviewBadge() {
  const { selectedRepo } = useRepos()
  const [summary, setSummary] = useState<QualitySummary | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!selectedRepo) {
      setSummary(null)
      return
    }

    const loadSummary = async () => {
      setLoading(true)
      try {
        const response = await analyseStatiqueClient.get(`/summary/${selectedRepo.id}`)
        const data = response.data?.summary || response.data
        if (data && data.file_count !== undefined) {
          setSummary({
            file_count: data.file_count || 0,
            avg_cyclomatic_complexity: data.avg_cyclomatic_complexity || 0,
            total_code_smells: data.total_code_smells || 0
          })
        } else {
          setSummary(null)
        }
      } catch (e) {
        console.warn('Failed to load summary for repo:', selectedRepo.id)
        setSummary(null)
      } finally {
        setLoading(false)
      }
    }

    loadSummary()
  }, [selectedRepo])

  if (!selectedRepo) {
    return (
      <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
        Quality Overview – Aucun dépôt sélectionné
      </span>
    )
  }

  if (loading) {
    return (
      <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
        Quality Overview – Chargement...
      </span>
    )
  }

  if (!summary) {
    return (
      <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
        Quality Overview – {selectedRepo.name}
      </span>
    )
  }

  return (
    <div className="flex items-center gap-4">
      <span className="text-sm font-semibold text-slate-800 dark:text-slate-200">
        {selectedRepo.name}
      </span>
      <div className="flex items-center gap-3 text-xs">
        <span className="rounded-full bg-blue-100 px-2 py-0.5 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">
          {summary.file_count} fichiers
        </span>
        <span className={`rounded-full px-2 py-0.5 ${summary.avg_cyclomatic_complexity > 20
          ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
          : summary.avg_cyclomatic_complexity > 10
            ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300'
            : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
          }`}>
          CC moy: {summary.avg_cyclomatic_complexity.toFixed(1)}
        </span>
        <span className={`rounded-full px-2 py-0.5 ${summary.total_code_smells > 10
          ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
          : summary.total_code_smells > 5
            ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300'
            : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
          }`}>
          {summary.total_code_smells} smells
        </span>
      </div>
    </div>
  )
}

export function DashboardLayout() {
  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-50">
      {/* Sidebar */}
      <aside className="flex w-64 flex-col border-r border-slate-200 bg-white/90 dark:border-slate-800 dark:bg-sidebar">
        <div className="flex h-16 items-center gap-3 border-b border-slate-200 px-6 dark:border-slate-800">
          <img
            src={testscopeLogo}
            alt="TestScope logo"
            className="h-8 w-8"
          />
          <span className="text-lg font-semibold tracking-tight">
            TestScope
          </span>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1 text-sm">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `block rounded-md px-3 py-2 font-medium transition-colors duration-150 ${isActive
                ? 'bg-primary-600 text-white'
                : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800'
              }`
            }
          >
            Overview
          </NavLink>
          <NavLink
            to="/advanced-dashboard"
            className={({ isActive }) =>
              `block rounded-md px-3 py-2 font-medium transition-colors duration-150 ${isActive
                ? 'bg-primary-600 text-white'
                : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800'
              }`
            }
          >
            Dashboard Avancé
          </NavLink>
          <NavLink
            to="/connect-repo"
            className={({ isActive }) =>
              `block rounded-md px-3 py-2 font-medium transition-colors duration-150 ${isActive
                ? 'bg-primary-600 text-white'
                : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800'
              }`
            }
          >
            Connect repo
          </NavLink>
          <NavLink
            to="/analyse-statique"
            className={({ isActive }) =>
              `block rounded-md px-3 py-2 font-medium transition-colors duration-150 ${isActive
                ? 'bg-primary-600 text-white'
                : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800'
              }`
            }
          >
            Analyse Statique
          </NavLink>
          <NavLink
            to="/models"
            className={({ isActive }) =>
              `block rounded-md px-3 py-2 font-medium transition-colors duration-150 ${isActive
                ? 'bg-primary-600 text-white'
                : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800'
              }`
            }
          >
            ML Models
          </NavLink>
          <NavLink
            to="/test-plan"
            className={({ isActive }) =>
              `block rounded-md px-3 py-2 font-medium transition-colors duration-150 ${isActive
                ? 'bg-primary-600 text-white'
                : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800'
              }`
            }
          >
            Plan de Tests
          </NavLink>
        </nav>
      </aside>

      {/* Main area */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* Topbar */}
        <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur-sm sm:px-6 dark:border-slate-800 dark:bg-topbar/90">
          <div className="flex items-center gap-2">
            <QualityOverviewBadge />
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-500 dark:text-slate-400">
            <ThemeToggle />
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto bg-slate-50 dark:bg-slate-950">
          <div className="mx-auto flex max-w-6xl flex-col gap-6 p-4 sm:p-6 lg:p-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
