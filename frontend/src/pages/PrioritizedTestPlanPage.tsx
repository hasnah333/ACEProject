import { useState } from 'react'
import { prioritize } from '../services/api/priorisationService'
import type { PrioritizationRequest, PrioritizationResponse } from '../services/api/priorisationService'
import { UiCard } from '../components/ui/UiCard'

export function PrioritizedTestPlanPage() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<PrioritizationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [budget, setBudget] = useState(1000)
  const [repoId, setRepoId] = useState<number | undefined>(undefined)

  const handlePrioritize = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Example items - in production, these would come from ML Service predictions
      const exampleItems: PrioritizationRequest = {
        repo_id: repoId,
        items: [
          { id: 'file1.java', risk: 0.85, effort: 150, criticite: 1.5, module: 'core' },
          { id: 'file2.java', risk: 0.72, effort: 200, criticite: 1.2, module: 'api' },
          { id: 'file3.java', risk: 0.65, effort: 100, criticite: 1.0, module: 'utils' },
          { id: 'file4.java', risk: 0.58, effort: 80, criticite: 0.8, module: 'utils' },
          { id: 'file5.java', risk: 0.45, effort: 120, criticite: 1.1, module: 'core' },
        ],
        budget: budget,
        weights: {
          risk: 1.0,
          crit: 0.5,
        },
      }
      
      const response = await prioritize(exampleItems)
      setResult(response)
    } catch (err: any) {
      setError(err.message || 'Failed to generate prioritization plan')
    } finally {
      setLoading(false)
    }
  }

  // Pas besoin de columns, on va créer le tableau manuellement

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
          Prioritized Test Plan
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Generate an optimized test plan based on ML predictions and business constraints.
        </p>
      </div>

      <UiCard>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Budget (effort units)
              </label>
              <input
                type="number"
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                className="w-full px-3 py-2 border border-slate-300 rounded-md dark:bg-slate-800 dark:border-slate-600"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Repository ID (optional)
              </label>
              <input
                type="number"
                value={repoId || ''}
                onChange={(e) => setRepoId(e.target.value ? Number(e.target.value) : undefined)}
                className="w-full px-3 py-2 border border-slate-300 rounded-md dark:bg-slate-800 dark:border-slate-600"
              />
            </div>
          </div>
          
          <button
            onClick={handlePrioritize}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Generating...' : 'Generate Prioritized Plan'}
          </button>
        </div>
      </UiCard>

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
              <div>
                <div className="text-sm text-slate-500 dark:text-slate-400">Budget</div>
                <div className="text-lg font-semibold">{result.summary.budget}</div>
              </div>
              <div>
                <div className="text-sm text-slate-500 dark:text-slate-400">Effort Selected</div>
                <div className="text-lg font-semibold">{result.summary.effort_selected}</div>
              </div>
              <div>
                <div className="text-sm text-slate-500 dark:text-slate-400">Items Selected</div>
                <div className="text-lg font-semibold">{result.summary.items_selected} / {result.summary.items_total}</div>
              </div>
              <div>
                <div className="text-sm text-slate-500 dark:text-slate-400">Utilization</div>
                <div className="text-lg font-semibold">
                  {((result.summary.effort_selected / result.summary.budget) * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          </UiCard>

          <UiCard>
            <h2 className="text-lg font-semibold mb-4">Prioritized Plan</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-100 dark:bg-slate-800">
                  <tr>
                    <th className="px-4 py-2 text-left">Rank</th>
                    <th className="px-4 py-2 text-left">File ID</th>
                    <th className="px-4 py-2 text-left">Module</th>
                    <th className="px-4 py-2 text-left">Risk</th>
                    <th className="px-4 py-2 text-left">Effort</th>
                    <th className="px-4 py-2 text-left">Priority</th>
                    <th className="px-4 py-2 text-left">Selected</th>
                    <th className="px-4 py-2 text-left">Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                  {result.plan.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50 dark:hover:bg-slate-800">
                      <td className="px-4 py-2">{item.rank}</td>
                      <td className="px-4 py-2">{item.id}</td>
                      <td className="px-4 py-2">{item.module || 'N/A'}</td>
                      <td className="px-4 py-2">{item.risk.toFixed(3)}</td>
                      <td className="px-4 py-2">{item.effort}</td>
                      <td className="px-4 py-2">{item.priority_score.toFixed(3)}</td>
                      <td className="px-4 py-2">{item.selected ? '✓' : '✗'}</td>
                      <td className="px-4 py-2">{item.selection_reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </UiCard>
        </>
      )}
    </div>
  )
}

