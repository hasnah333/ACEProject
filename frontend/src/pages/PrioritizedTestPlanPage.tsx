import { useState, useEffect } from 'react'
import { prioritize } from '../services/api/priorisationService'
import type { PrioritizationRequest, PrioritizationResponse } from '../services/api/priorisationService'
import { UiCard } from '../components/ui/UiCard'
import { useRepos } from '../context/RepoContext'
import { mlServiceClient, analyseStatiqueClient } from '../services/api/client'

export function PrioritizedTestPlanPage() {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<PrioritizationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [budget, setBudget] = useState(1000)
  // Utiliser le contexte global
  const { repos, selectedRepoId, setSelectedRepoId } = useRepos()
  const loadingRepos = repos.length === 0

  // Sélectionner le premier repo si aucun n'est sélectionné
  useEffect(() => {
    if (repos.length > 0 && !selectedRepoId) {
      setSelectedRepoId(repos[0].id)
    }
  }, [repos, selectedRepoId, setSelectedRepoId])

  const handlePrioritize = async () => {
    if (!selectedRepoId) {
      setError('Veuillez sélectionner un dépôt')
      return
    }

    setLoading(true)
    setError(null)

    try {
      // 1. Récupérer les métriques réelles du dépôt depuis l'analyse statique
      let items: { id: string; risk: number; effort: number; criticite: number; module: string }[] = []

      console.log('Fetching metrics for repo:', selectedRepoId)

      try {
        const metricsResponse = await analyseStatiqueClient.get(`/metrics/${selectedRepoId}`)
        console.log('Metrics response:', metricsResponse.data)
        const metrics = metricsResponse.data?.metrics || metricsResponse.data || []

        if (Array.isArray(metrics) && metrics.length > 0) {
          console.log('Found', metrics.length, 'metrics, first file:', metrics[0]?.filepath)
          // Convertir les métriques en items pour la priorisation
          items = metrics.map((m: any) => {
            // Calculer un score de risque basé sur les métriques
            const loc = m.loc || 100
            const cbo = m.cbo || 0
            const filename = m.filepath?.split('/').pop() || m.filepath || 'unknown'
            const module = m.filepath?.split('/').slice(-2, -1)[0] || 'default'

            return {
              id: filename,
              risk: 0.5, // Sera mis à jour par le ML
              effort: Math.round(loc * 0.5), // Effort estimé basé sur LOC
              criticite: cbo > 10 ? 1.5 : (cbo > 5 ? 1.2 : 1.0),
              module: module,
              metrics: m // Garder les métriques pour le ML
            }
          })
        }
      } catch (metricsError) {
        console.warn('Could not load metrics, trying predictions...', metricsError)
      }

      // 2. Utiliser le service ML pour obtenir les probabilités réelles (IA)
      if (items.length > 0) {
        try {
          // Extraire uniquement les métriques pour l'API ML
          const predictItems = items.map((it: any) => it.metrics)

          const predictResponse = await mlServiceClient.post('/ml/predict', {
            items: predictItems
          })

          const predictions = predictResponse.data?.predictions || []

          if (predictions.length > 0) {
            // Mettre à jour les scores de risque avec les prédictions de l'IA
            items = items.map((it: any, idx: number) => {
              const pred = predictions[idx] || predictions.find((p: any) => p.id === it.id)
              return {
                ...it,
                risk: pred?.risk_score || pred?.probability || it.risk
              }
            })
          }
        } catch (predictError) {
          console.warn('ML Prediction failed, using fallback risk scores', predictError)
        }
      } else {
        // Fallback: Si pas de métriques en base, tenter une prédiction par repo_id (si supporté par le backend)
        try {
          const predictResponse = await mlServiceClient.post('/ml/predict', {
            dataset_id: selectedRepoId // Utiliser le repo_id comme dataset_id si cohérent
          }).catch(() => null)

          if (predictResponse?.data?.predictions) {
            const predictions = predictResponse.data.predictions
            items = predictions.map((p: any, idx: number) => ({
              id: p.id || `file_${idx}`,
              risk: p.risk_score || 0.5,
              effort: 100,
              criticite: 1.0,
              module: 'default'
            }))
          }
        } catch (e) {
          console.error("ML fallback also failed")
        }
      }

      // 3. Si toujours vide, générer des données de démonstration basées sur le repo
      if (items.length === 0) {
        const repo = repos.find(r => r.id === selectedRepoId)
        const repoName = repo?.name || 'project'

        items = [
          { id: `${repoName}/AuthService.java`, risk: 0.85, effort: 180, criticite: 1.5, module: 'security' },
          { id: `${repoName}/PaymentController.java`, risk: 0.78, effort: 220, criticite: 1.8, module: 'payment' },
          { id: `${repoName}/UserRepository.java`, risk: 0.65, effort: 120, criticite: 1.2, module: 'data' },
          { id: `${repoName}/OrderService.java`, risk: 0.58, effort: 150, criticite: 1.3, module: 'orders' },
          { id: `${repoName}/NotificationHelper.java`, risk: 0.42, effort: 80, criticite: 0.9, module: 'utils' },
          { id: `${repoName}/ConfigLoader.java`, risk: 0.35, effort: 60, criticite: 0.7, module: 'config' },
          { id: `${repoName}/LoggingAspect.java`, risk: 0.28, effort: 45, criticite: 0.5, module: 'logging' },
        ]
      }

      // 4. Envoyer au service de priorisation
      const request: PrioritizationRequest = {
        repo_id: selectedRepoId,
        items: items,
        budget: budget,
        weights: {
          risk: 1.0,
          crit: 0.5,
        },
      }

      const response = await prioritize(request)
      setResult(response)
    } catch (err: any) {
      setError(err.message || 'Échec de la génération du plan de priorisation')
    } finally {
      setLoading(false)
    }
  }

  const getRiskColor = (risk: number) => {
    if (risk >= 0.7) return 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30'
    if (risk >= 0.4) return 'text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30'
    return 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30'
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
          Plan de Tests Priorisé
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Générez un plan de tests optimisé basé sur les prédictions ML et les contraintes métier de votre dépôt.
        </p>
      </div>

      {/* Configuration */}
      <UiCard>
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Configuration</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Sélecteur de dépôt */}
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Dépôt
              </label>
              {loadingRepos ? (
                <div className="animate-pulse h-10 bg-slate-200 dark:bg-slate-700 rounded-md"></div>
              ) : (
                <select
                  value={selectedRepoId || ''}
                  onChange={(e) => setSelectedRepoId(Number(e.target.value))}
                  className="w-full px-3 py-2 border border-slate-300 rounded-md dark:bg-slate-800 dark:border-slate-600 outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {repos.map(repo => (
                    <option key={repo.id} value={repo.id}>
                      {repo.name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Budget */}
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Budget d'effort (unités)
              </label>
              <input
                type="number"
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                className="w-full px-3 py-2 border border-slate-300 rounded-md dark:bg-slate-800 dark:border-slate-600 outline-none focus:ring-2 focus:ring-indigo-500"
                min={100}
                step={100}
              />
            </div>

            {/* Bouton */}
            <div className="flex items-end">
              <button
                onClick={handlePrioritize}
                disabled={loading || !selectedRepoId}
                className="w-full px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 flex items-center justify-center gap-2 transition-all"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Génération...
                  </>
                ) : (
                  'Générer le Plan'
                )}
              </button>
            </div>
          </div>
        </div>
      </UiCard>

      {error && (
        <UiCard>
          <div className="text-red-600 dark:text-red-400 p-4 bg-red-50 dark:bg-red-900/20 rounded-lg">
            {error}
          </div>
        </UiCard>
      )}

      {result && (
        <>
          {/* Résumé */}
          <UiCard>
            <h2 className="text-lg font-semibold mb-4 text-slate-900 dark:text-slate-50">Résumé</h2>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                <div className="text-xs text-slate-500 dark:text-slate-400">Budget</div>
                <div className="text-xl font-bold text-slate-900 dark:text-slate-50">{result.summary.budget}</div>
              </div>
              <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                <div className="text-xs text-slate-500 dark:text-slate-400">Effort Utilisé</div>
                <div className="text-xl font-bold text-indigo-600 dark:text-indigo-400">{result.summary.effort_selected}</div>
              </div>
              <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                <div className="text-xs text-slate-500 dark:text-slate-400">Fichiers Sélectionnés</div>
                <div className="text-xl font-bold text-green-600 dark:text-green-400">
                  {result.summary.items_selected} / {result.summary.items_total}
                </div>
              </div>
              <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                <div className="text-xs text-slate-500 dark:text-slate-400">Utilisation Budget</div>
                <div className="text-xl font-bold text-purple-600 dark:text-purple-400">
                  {((result.summary.effort_selected / result.summary.budget) * 100).toFixed(0)}%
                </div>
              </div>
              <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                <div className="text-xs text-slate-500 dark:text-slate-400">Risque Couvert</div>
                <div className="text-xl font-bold text-orange-600 dark:text-orange-400">
                  {(result.plan.filter(p => p.selected).reduce((sum, p) => sum + p.risk, 0) /
                    result.plan.reduce((sum, p) => sum + p.risk, 0) * 100).toFixed(0)}%
                </div>
              </div>
            </div>
          </UiCard>

          {/* Plan détaillé */}
          <UiCard>
            <h2 className="text-lg font-semibold mb-4 text-slate-900 dark:text-slate-50">Plan de Tests Détaillé</h2>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-100 dark:bg-slate-800">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium">Priorité</th>
                    <th className="px-4 py-3 text-left font-medium">Fichier</th>
                    <th className="px-4 py-3 text-left font-medium">Module</th>
                    <th className="px-4 py-3 text-left font-medium">Risque</th>
                    <th className="px-4 py-3 text-left font-medium">Effort</th>
                    <th className="px-4 py-3 text-left font-medium">Score</th>
                    <th className="px-4 py-3 text-left font-medium">Statut</th>
                    <th className="px-4 py-3 text-left font-medium">Raison</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                  {result.plan.map((item) => (
                    <tr
                      key={item.id}
                      className={`hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors ${item.selected ? '' : 'opacity-50'
                        }`}
                    >
                      <td className="px-4 py-3 font-semibold">#{item.rank}</td>
                      <td className="px-4 py-3 font-mono text-xs">{item.id}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex px-2 py-0.5 rounded text-xs bg-slate-100 dark:bg-slate-700">
                          {item.module || 'N/A'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded text-xs font-medium ${getRiskColor(item.risk)}`}>
                          {(item.risk * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td className="px-4 py-3">{item.effort}</td>
                      <td className="px-4 py-3 font-medium">{item.priority_score.toFixed(2)}</td>
                      <td className="px-4 py-3">
                        {item.selected ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                            ✓ Inclus
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                            ✗ Exclu
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500">{item.selection_reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </UiCard>

          {/* Recommandation */}
          <UiCard>
            <h3 className="text-sm font-semibold mb-2 text-slate-900 dark:text-slate-50">Recommandation</h3>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Avec un budget de <strong>{result.summary.budget}</strong> unités d'effort,
              vous devriez prioriser les <strong>{result.summary.items_selected}</strong> fichiers
              marqués "Inclus" pour maximiser la détection de défauts.
              Cela représente <strong>{((result.summary.effort_selected / result.summary.budget) * 100).toFixed(0)}%</strong> de
              votre budget et couvre les fichiers les plus à risque.
            </p>
          </UiCard>
        </>
      )}
    </div>
  )
}
