import { useState, useEffect } from 'react'
import { prioritize } from '../services/api/priorisationService'
import type { PrioritizationRequest, PrioritizationResponse, PrioritizationItem } from '../services/api/priorisationService'
import { listRepos } from '../services/api/repoService'
import type { Repo } from '../services/api/repoService'
import { backendClient } from '../services/api/client'
import { UiCard } from '../components/ui/UiCard'

interface FileMetric {
  filepath: string
  cyclomatic_complexity: number
  wmc: number
  cbo: number
  loc: number
  code_smells_count: number
}

export function PrioritizedTestPlanPage() {
  const [repos, setRepos] = useState<Repo[]>([])
  const [selectedRepoId, setSelectedRepoId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingFiles, setLoadingFiles] = useState(false)
  const [result, setResult] = useState<PrioritizationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [budget, setBudget] = useState(1000)
  const [files, setFiles] = useState<FileMetric[]>([])

  useEffect(() => {
    loadRepos()
  }, [])

  useEffect(() => {
    if (selectedRepoId) {
      loadFiles(selectedRepoId)
    }
  }, [selectedRepoId])

  const loadRepos = async () => {
    try {
      const reposList = await listRepos()
      setRepos(reposList)
      if (reposList.length > 0) {
        setSelectedRepoId(reposList[0].id)
      }
    } catch (err) {
      console.error('Failed to load repos:', err)
    }
  }

  const loadFiles = async (repoId: number) => {
    setLoadingFiles(true)
    try {
      // Utiliser le proxy via backend pour analyse-statique
      const response = await backendClient.get(`/api/analyse/metrics/${repoId}`)
      const metrics = response.data.metrics || []
      setFiles(metrics)
      setError(null)
    } catch (err: unknown) {
      console.error('Failed to load file metrics:', err)
      // Essayer endpoint direct
      try {
        const resp = await fetch(`http://localhost:8005/metrics/${repoId}`)
        const data = await resp.json()
        setFiles(data.metrics || [])
      } catch {
        setError('No file metrics found. Run static analysis first.')
        setFiles([])
      }
    } finally {
      setLoadingFiles(false)
    }
  }

  const calculateRiskScore = (file: FileMetric): number => {
    let score = 0
    const ccNorm = Math.min((file.cyclomatic_complexity || 0) / 50, 1)
    score += ccNorm * 0.3
    const wmcNorm = Math.min((file.wmc || 0) / 100, 1)
    score += wmcNorm * 0.2
    const cboNorm = Math.min((file.cbo || 0) / 20, 1)
    score += cboNorm * 0.2
    const smellsNorm = Math.min((file.code_smells_count || 0) / 10, 1)
    score += smellsNorm * 0.2
    const locNorm = Math.min((file.loc || 0) / 500, 1)
    score += locNorm * 0.1
    return Math.min(score, 1)
  }

  const getShortFilename = (filepath: string): string => {
    const parts = filepath.split('/')
    return parts[parts.length - 1]
  }

  const handlePrioritize = async () => {
    if (!selectedRepoId || files.length === 0) {
      setError('Please select a repository with analyzed files')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const items: PrioritizationItem[] = files.map((file) => {
        const riskScore = calculateRiskScore(file)
        const effort = Math.max(10, Math.round((file.loc || 100) * 0.5 + (file.cyclomatic_complexity || 5) * 5))
        const pathParts = file.filepath.split('/')
        const module = pathParts.length > 1 ? pathParts[0] : 'root'

        return {
          id: file.filepath,
          risk: riskScore,
          effort: effort,
          criticite: 1 + ((file.code_smells_count || 0) * 0.1),
          module: module,
        }
      })

      const request: PrioritizationRequest = {
        repo_id: selectedRepoId,
        items: items,
        budget: budget,
        weights: { risk: 1.0, crit: 0.5 },
      }

      const response = await prioritize(request)
      setResult(response)
    } catch (err: unknown) {
      const e = err as { message?: string }
      setError(e.message || 'Failed to generate prioritization plan')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
          Plan de Tests Priorisé
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Générez un plan de tests optimisé basé sur les métriques du code.
        </p>
      </div>

      <UiCard>
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Repository
              </label>
              <select
                value={selectedRepoId || ''}
                onChange={(e) => setSelectedRepoId(Number(e.target.value))}
                className="w-full px-3 py-2 border border-slate-300 rounded-md dark:bg-slate-800 dark:border-slate-600"
              >
                <option value="">Select a repository</option>
                {repos.map(repo => (
                  <option key={repo.id} value={repo.id}>{repo.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Budget (effort)
              </label>
              <input
                type="number"
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                min={100}
                className="w-full px-3 py-2 border border-slate-300 rounded-md dark:bg-slate-800 dark:border-slate-600"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Files
              </label>
              <div className="px-3 py-2 bg-slate-100 dark:bg-slate-700 rounded-md">
                {loadingFiles ? 'Loading...' : `${files.length} files`}
              </div>
            </div>
          </div>

          <button
            onClick={handlePrioritize}
            disabled={loading || files.length === 0}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Generating...' : 'Generate Prioritized Plan'}
          </button>
        </div>
      </UiCard>

      {files.length > 0 && !result && (
        <UiCard>
          <h2 className="text-lg font-semibold mb-4">Files to Prioritize ({files.length})</h2>
          <div className="max-h-64 overflow-y-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-100 dark:bg-slate-800 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left">File</th>
                  <th className="px-4 py-2 text-left">LOC</th>
                  <th className="px-4 py-2 text-left">CC</th>
                  <th className="px-4 py-2 text-left">Risk</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                {files.map((file) => (
                  <tr key={file.filepath}>
                    <td className="px-4 py-2" title={file.filepath}>{getShortFilename(file.filepath)}</td>
                    <td className="px-4 py-2">{file.loc}</td>
                    <td className="px-4 py-2">{file.cyclomatic_complexity}</td>
                    <td className="px-4 py-2">{(calculateRiskScore(file) * 100).toFixed(0)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </UiCard>
      )}

      {error && (
        <UiCard>
          <div className="text-red-600 dark:text-red-400">{error}</div>
        </UiCard>
      )}

      {result && (
        <>
          <UiCard>
            <h2 className="text-lg font-semibold mb-4">Summary</h2>
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-blue-50 dark:bg-blue-900/20 p-4 rounded-lg">
                <div className="text-sm text-slate-500">Budget</div>
                <div className="text-2xl font-bold text-blue-600">{result.summary.budget}</div>
              </div>
              <div className="bg-green-50 dark:bg-green-900/20 p-4 rounded-lg">
                <div className="text-sm text-slate-500">Effort Used</div>
                <div className="text-2xl font-bold text-green-600">{result.summary.effort_selected}</div>
              </div>
              <div className="bg-purple-50 dark:bg-purple-900/20 p-4 rounded-lg">
                <div className="text-sm text-slate-500">Selected</div>
                <div className="text-2xl font-bold text-purple-600">
                  {result.summary.items_selected} / {result.summary.items_total}
                </div>
              </div>
              <div className="bg-orange-50 dark:bg-orange-900/20 p-4 rounded-lg">
                <div className="text-sm text-slate-500">Utilization</div>
                <div className="text-2xl font-bold text-orange-600">
                  {((result.summary.effort_selected / result.summary.budget) * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          </UiCard>

          <UiCard>
            <h2 className="text-lg font-semibold mb-4">Prioritized Plan</h2>
            <table className="min-w-full text-sm">
              <thead className="bg-slate-100 dark:bg-slate-800">
                <tr>
                  <th className="px-4 py-2 text-left">Rank</th>
                  <th className="px-4 py-2 text-left">File</th>
                  <th className="px-4 py-2 text-left">Module</th>
                  <th className="px-4 py-2 text-left">Risk</th>
                  <th className="px-4 py-2 text-left">Effort</th>
                  <th className="px-4 py-2 text-center">Selected</th>
                  <th className="px-4 py-2 text-left">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                {result.plan.map((item) => (
                  <tr key={item.id} className={item.selected ? 'bg-green-50 dark:bg-green-900/10' : ''}>
                    <td className="px-4 py-2 font-bold">{item.rank}</td>
                    <td className="px-4 py-2 font-medium" title={item.id}>{getShortFilename(item.id)}</td>
                    <td className="px-4 py-2">{item.module || 'root'}</td>
                    <td className="px-4 py-2">{(item.risk * 100).toFixed(0)}%</td>
                    <td className="px-4 py-2">{item.effort}</td>
                    <td className="px-4 py-2 text-center">
                      {item.selected ? <span className="text-green-600 text-xl">✓</span> : <span className="text-slate-400">✗</span>}
                    </td>
                    <td className="px-4 py-2 text-xs text-slate-500">{item.selection_reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </UiCard>
        </>
      )}
    </div>
  )
}
