import { NavLink, Outlet } from 'react-router-dom'
import { ThemeToggle } from '../components/ui/ThemeToggle'
import testscopeLogo from '../assets/testscope-logo.svg'

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
            to="/ml-pipeline"
            className={({ isActive }) =>
              `block rounded-md px-3 py-2 font-medium transition-colors duration-150 ${isActive
                ? 'bg-primary-600 text-white'
                : 'text-slate-700 hover:bg-slate-100 dark:text-slate-200 dark:hover:bg-slate-800'
              }`
            }
          >
            ML Pipeline
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
            <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Quality Overview
            </span>
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


