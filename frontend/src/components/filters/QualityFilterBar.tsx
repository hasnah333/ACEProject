import { useState, useRef, useEffect } from 'react'
import { listRepos } from '../../services/api/repoService'
import type { Repo } from '../../services/api/repoService'

interface FilterBarProps {
  onFilterChange?: (filters: FilterState) => void
}

interface FilterState {
  timeRange: string
  repoId: string | null
  signal: string
}

const TIME_OPTIONS = [
  { label: 'Last 7 days', value: '7d' },
  { label: 'Last 30 days', value: '30d' },
  { label: 'Last 90 days', value: '90d' },
  { label: 'All time', value: 'all' },
]

const SIGNAL_OPTIONS = [
  { label: 'Test quality', value: 'test_quality' },
  { label: 'Code coverage', value: 'coverage' },
  { label: 'Code smells', value: 'smells' },
  { label: 'Risk score', value: 'risk' },
]

export function QualityFilterBar({ onFilterChange }: FilterBarProps) {
  const [filters, setFilters] = useState<FilterState>({
    timeRange: '30d',
    repoId: null,
    signal: 'test_quality'
  })
  const [repos, setRepos] = useState<Repo[]>([])
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadRepos()
    // Close dropdown when clicking outside
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setActiveDropdown(null)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const loadRepos = async () => {
    try {
      const reposList = await listRepos()
      setRepos(reposList)
    } catch (e) {
      console.error('Failed to load repos', e)
    }
  }

  const handleFilterChange = (key: keyof FilterState, value: string | null) => {
    const newFilters = { ...filters, [key]: value }
    setFilters(newFilters)
    setActiveDropdown(null)
    onFilterChange?.(newFilters)
  }

  const getTimeLabel = () => TIME_OPTIONS.find(o => o.value === filters.timeRange)?.label || 'Last 30 days'
  const getRepoLabel = () => {
    if (!filters.repoId) return 'All repos'
    return repos.find(r => r.id.toString() === filters.repoId)?.name || 'All repos'
  }
  const getSignalLabel = () => SIGNAL_OPTIONS.find(o => o.value === filters.signal)?.label || 'Test quality'

  return (
    <div className="flex flex-wrap gap-2 items-center text-xs" ref={dropdownRef}>
      <span className="text-slate-400">Filters</span>

      {/* Time Filter */}
      <div className="relative">
        <button
          onClick={() => setActiveDropdown(activeDropdown === 'time' ? null : 'time')}
          className="inline-flex items-center gap-1 rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1 text-slate-200 hover:bg-slate-800 transition-colors"
        >
          Time: {getTimeLabel()}
          <svg className="w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {activeDropdown === 'time' && (
          <div className="absolute top-full left-0 mt-1 w-36 bg-slate-800 border border-slate-700 rounded-lg shadow-lg z-50 overflow-hidden">
            {TIME_OPTIONS.map(option => (
              <button
                key={option.value}
                onClick={() => handleFilterChange('timeRange', option.value)}
                className={`w-full text-left px-3 py-2 hover:bg-slate-700 transition-colors ${filters.timeRange === option.value ? 'bg-indigo-600 text-white' : 'text-slate-200'
                  }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Repo Filter */}
      <div className="relative">
        <button
          onClick={() => setActiveDropdown(activeDropdown === 'repo' ? null : 'repo')}
          className="inline-flex items-center gap-1 rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1 text-slate-200 hover:bg-slate-800 transition-colors"
        >
          Scope: {getRepoLabel()}
          <svg className="w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {activeDropdown === 'repo' && (
          <div className="absolute top-full left-0 mt-1 w-48 bg-slate-800 border border-slate-700 rounded-lg shadow-lg z-50 overflow-hidden max-h-48 overflow-y-auto">
            <button
              onClick={() => handleFilterChange('repoId', null)}
              className={`w-full text-left px-3 py-2 hover:bg-slate-700 transition-colors ${!filters.repoId ? 'bg-indigo-600 text-white' : 'text-slate-200'
                }`}
            >
              All repos
            </button>
            {repos.map(repo => (
              <button
                key={repo.id}
                onClick={() => handleFilterChange('repoId', repo.id.toString())}
                className={`w-full text-left px-3 py-2 hover:bg-slate-700 transition-colors truncate ${filters.repoId === repo.id.toString() ? 'bg-indigo-600 text-white' : 'text-slate-200'
                  }`}
              >
                {repo.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Signal Filter */}
      <div className="relative">
        <button
          onClick={() => setActiveDropdown(activeDropdown === 'signal' ? null : 'signal')}
          className="inline-flex items-center gap-1 rounded-full border border-slate-700 bg-slate-900/70 px-3 py-1 text-slate-200 hover:bg-slate-800 transition-colors"
        >
          Signal: {getSignalLabel()}
          <svg className="w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>
        {activeDropdown === 'signal' && (
          <div className="absolute top-full left-0 mt-1 w-40 bg-slate-800 border border-slate-700 rounded-lg shadow-lg z-50 overflow-hidden">
            {SIGNAL_OPTIONS.map(option => (
              <button
                key={option.value}
                onClick={() => handleFilterChange('signal', option.value)}
                className={`w-full text-left px-3 py-2 hover:bg-slate-700 transition-colors ${filters.signal === option.value ? 'bg-indigo-600 text-white' : 'text-slate-200'
                  }`}
              >
                {option.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
