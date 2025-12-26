import { useState, useEffect } from 'react'
import { backendClient, mlServiceClient, analyseStatiqueClient } from '../../services/api/client'

interface SummaryData {
  label: string
  value: string
  trend: string
  tone: 'good' | 'warn' | 'bad'
}

export function QualitySummaryCards() {
  const [summary, setSummary] = useState<SummaryData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSummaryData()
  }, [])

  const loadSummaryData = async () => {
    setLoading(true)
    try {
      // Charger les données réelles depuis tous les services
      const [reposResponse, modelsResponse] = await Promise.allSettled([
        backendClient.get('/api/repos'),
        mlServiceClient.get('/ml/models/list')
      ])

      let repoCount = 0
      let repos: any[] = []

      if (reposResponse.status === 'fulfilled') {
        repos = Array.isArray(reposResponse.value.data) ? reposResponse.value.data : (reposResponse.value.data?.repos || [])
        repoCount = repos.length
      }


      let modelCount = 0
      let bestAccuracy = 0

      if (modelsResponse.status === 'fulfilled') {
        const models = Array.isArray(modelsResponse.value.data) ? modelsResponse.value.data : (modelsResponse.value.data?.models || [])
        // Filtrer uniquement les modèles actifs pour une meilleure représentation
        const activeModels = models.filter((m: any) => m.is_active !== false)
        modelCount = models.length
        if (activeModels.length > 0) {
          bestAccuracy = Math.max(...activeModels.map((m: any) => m.metrics?.accuracy || m.accuracy || 0))
        }
      }

      // Charger les métriques réelles depuis TOUS les repos (pas juste le premier)
      let avgComplexity = 0
      let totalSmells = 0
      let totalFiles = 0

      // Agréger les métriques de tous les repos
      for (const repo of repos) {
        try {
          const metricsResponse = await analyseStatiqueClient.get(`/metrics/${repo.id}`)
          const metrics = metricsResponse?.data?.metrics || []

          if (Array.isArray(metrics) && metrics.length > 0) {
            totalFiles += metrics.length
            metrics.forEach((m: any) => {
              avgComplexity += m.cyclomatic_complexity || 0
              totalSmells += m.code_smells_count || 0
            })
          }
        } catch (e) {
          console.warn(`Failed to load metrics for repo ${repo.id}`)
        }
      }

      // Calculer la moyenne de complexité
      avgComplexity = totalFiles > 0 ? avgComplexity / totalFiles : 0

      // Calculer la couverture estimée basée sur les métriques
      const estimatedCoverage = Math.max(50, Math.min(95, 100 - avgComplexity * 2 - totalSmells / 5))

      setSummary([
        {
          label: 'Code Quality Score',
          value: `${Math.round(estimatedCoverage)}%`,
          trend: avgComplexity < 10 ? '↑ Low complexity' : avgComplexity < 20 ? '→ Medium' : '↓ High complexity',
          tone: estimatedCoverage >= 80 ? 'good' : estimatedCoverage >= 60 ? 'warn' : 'bad'
        },
        {
          label: 'ML Models',
          value: modelCount.toString(),
          trend: modelCount > 0 ? `Best: ${(bestAccuracy * 100).toFixed(0)}% accuracy` : 'Train a model',
          tone: bestAccuracy >= 0.9 ? 'good' : bestAccuracy >= 0.7 ? 'warn' : modelCount > 0 ? 'bad' : 'warn'
        },
        {
          label: 'Repositories',
          value: repoCount.toString(),
          trend: repoCount > 0 ? `${totalFiles} files analyzed` : 'Connect a repo',
          tone: repoCount > 0 ? 'good' : 'warn'
        },
        {
          label: 'Code Smells',
          value: totalSmells.toString(),
          trend: totalSmells > 20 ? 'Need attention' : totalSmells > 0 ? 'Under control' : 'Clean code!',
          tone: totalSmells > 30 ? 'bad' : totalSmells > 10 ? 'warn' : 'good'
        },
      ])
    } catch (error) {
      console.log('Using default summary data:', error)
      // Fallback aux données par défaut
      setSummary([
        { label: 'Code Quality Score', value: '85%', trend: '↑ Improving', tone: 'good' },
        { label: 'ML Models', value: '0', trend: 'Train a model', tone: 'warn' },
        { label: 'Repositories', value: '0', trend: 'Connect a repo', tone: 'warn' },
        { label: 'Code Smells', value: '0', trend: 'Analyze code', tone: 'warn' },
      ])
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="rounded-xl border border-slate-200/70 bg-white/80 px-4 py-3 shadow-sm dark:border-slate-800 dark:bg-slate-900/70 animate-pulse"
          >
            <div className="h-3 bg-slate-200 dark:bg-slate-700 rounded w-24 mb-2"></div>
            <div className="h-8 bg-slate-200 dark:bg-slate-700 rounded w-16"></div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {summary.map((item) => (
        <article
          key={item.label}
          className="rounded-xl border border-slate-200/70 bg-white/80 px-4 py-3 shadow-sm transition-all duration-200 hover:-translate-y-[1px] hover:shadow-md hover:border-slate-300 dark:border-slate-800 dark:bg-slate-900/70 dark:hover:border-slate-700"
        >
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
            {item.label}
          </p>
          <div className="mt-2 flex items-end justify-between">
            <p className="text-2xl font-semibold text-slate-900 dark:text-slate-50">
              {item.value}
            </p>
            <p
              className={`text-xs font-medium ${item.tone === 'good'
                ? 'text-emerald-400'
                : item.tone === 'warn'
                  ? 'text-amber-400'
                  : 'text-rose-400'
                }`}
            >
              {item.trend}
            </p>
          </div>
        </article>
      ))}
    </div>
  )
}
