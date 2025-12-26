import { UiCard } from '../components/ui/UiCard'
import { useState, useEffect } from 'react'
import { mlServiceClient, pretraitementClient } from '../services/api/client'
import { listRepos } from '../services/api/repoService'
import type { Repo } from '../services/api/repoService'

interface Model {
  model_id: string
  model_type: string | null
  created_at: string | null
  dataset_id: string | null
  repo_id: number | null
  is_active?: boolean
  is_best?: boolean
  metrics: {
    accuracy?: number
    precision?: number
    recall?: number
    f1_score?: number
    roc_auc?: number
    pr_auc?: number
  }
}

export function ModelsPage() {
  const [models, setModels] = useState<Model[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Training state
  const [showTrainForm, setShowTrainForm] = useState(false)
  const [repos, setRepos] = useState<Repo[]>([])
  const [trainingRepoId, setTrainingRepoId] = useState<number | null>(null)
  const [trainingStatus, setTrainingStatus] = useState<string>('')
  const [isTraining, setIsTraining] = useState(false)

  useEffect(() => {
    fetchModels()
    loadRepos()
  }, [])

  const loadRepos = async () => {
    try {
      const list = await listRepos()
      setRepos(list)
      if (list.length > 0) setTrainingRepoId(list[0].id)
    } catch (e) {
      console.error('Failed to load repos:', e)
    }
  }

  const handleTrain = async () => {
    if (!trainingRepoId) return

    setIsTraining(true)
    setTrainingStatus('Génération des features...')

    try {
      // 1. Generate features
      const featuresResp = await pretraitementClient.post('/features/generate', {
        repo_id: trainingRepoId,
        balancing_strategy: 'smote'
      })
      const datasetId = featuresResp.data?.dataset_id

      if (!datasetId) throw new Error('Dataset ID not returned')

      setTrainingStatus('Entraînement du modèle...')

      // 2. Train model
      await mlServiceClient.post('/ml/train/auto', {
        dataset_id: datasetId,
        repo_id: trainingRepoId,
        model_family: 'ensemble',
        target_metric: 'accuracy',
        n_trials: 20
      })

      setTrainingStatus('Modèle entraîné avec succès !')

      // Refresh models list
      await fetchModels()
      setShowTrainForm(false)

    } catch (err: any) {
      console.error('Training error:', err)
      setTrainingStatus(`Erreur: ${err.message || 'Échec de l\'entraînement'}`)
    } finally {
      setIsTraining(false)
    }
  }

  const fetchModels = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await mlServiceClient.get('/ml/models/list')

      let modelsData: Model[] = []
      if (Array.isArray(response.data)) {
        modelsData = response.data
      } else if (response.data && Array.isArray(response.data.models)) {
        modelsData = response.data.models
      } else if (response.data && response.data.model_id) {
        modelsData = [response.data]
      }

      setModels(modelsData)
    } catch (err: any) {
      console.error('Error fetching models:', err)
      setError(err.message || 'Erreur lors du chargement des modèles')
      setModels([])
    } finally {
      setLoading(false)
    }
  }

  const toggleModelStatus = async (modelId: string, currentStatus: boolean) => {
    setActionLoading(modelId)
    try {
      await mlServiceClient.put(`/ml/models/${modelId}/status`, {
        is_active: !currentStatus
      })
      // Mettre à jour localement
      setModels(prev => prev.map(m =>
        m.model_id === modelId ? { ...m, is_active: !currentStatus } : m
      ))
    } catch (err: any) {
      console.error('Error toggling model status:', err)
      alert('Erreur lors de la modification du statut')
    } finally {
      setActionLoading(null)
    }
  }

  const deleteModel = async (modelId: string) => {
    if (!confirm(`Êtes-vous sûr de vouloir supprimer le modèle ${modelId} ?`)) {
      return
    }

    setActionLoading(modelId)
    try {
      await mlServiceClient.delete(`/ml/models/${modelId}`)
      setModels(prev => prev.filter(m => m.model_id !== modelId))
    } catch (err: any) {
      console.error('Error deleting model:', err)
      alert('Erreur lors de la suppression du modèle')
    } finally {
      setActionLoading(null)
    }
  }

  const setAsBestModel = async (modelId: string) => {
    setActionLoading(modelId)
    try {
      await mlServiceClient.put(`/ml/models/${modelId}/set-best`)
      // Mettre à jour localement
      setModels(prev => prev.map(m => ({
        ...m,
        is_best: m.model_id === modelId
      })))
    } catch (err: any) {
      console.error('Error setting best model:', err)
      alert('Erreur lors de la définition du meilleur modèle')
    } finally {
      setActionLoading(null)
    }
  }

  const getAccuracyColor = (accuracy?: number) => {
    if (!accuracy) return 'text-gray-500'
    if (accuracy >= 0.9) return 'text-green-600 dark:text-green-400'
    if (accuracy >= 0.7) return 'text-yellow-600 dark:text-yellow-400'
    return 'text-red-600 dark:text-red-400'
  }

  const getStatusBadge = (model: Model) => {
    if (model.is_best) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200">
          Meilleur
        </span>
      )
    }
    if (model.is_active !== false) {
      return (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
          Actif
        </span>
      )
    }
    return (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300">
        Inactif
      </span>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-start">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
            Machine Learning Models
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Gestion et suivi des modèles ML entraînés. Activez, désactivez ou supprimez vos modèles.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowTrainForm(!showTrainForm)}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 flex items-center gap-2 transition-all"
          >
            + Entraîner
          </button>
          <button
            onClick={fetchModels}
            disabled={loading}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2 transition-all"
          >
            {loading ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            ) : (
              <span>Actualiser</span>
            )}
          </button>
        </div>
      </div>

      {/* Train Form */}
      {showTrainForm && (
        <UiCard>
          <h3 className="font-semibold mb-4">Entraîner un nouveau modèle</h3>
          <div className="flex flex-wrap gap-4 items-end">
            <div>
              <label className="block text-sm font-medium text-slate-600 dark:text-slate-300 mb-1">
                Repository
              </label>
              <select
                value={trainingRepoId || ''}
                onChange={(e) => setTrainingRepoId(Number(e.target.value))}
                className="px-3 py-2 border border-slate-300 rounded-md dark:bg-slate-800 dark:border-slate-600"
                disabled={isTraining}
              >
                {repos.map(repo => (
                  <option key={repo.id} value={repo.id}>{repo.name}</option>
                ))}
              </select>
            </div>
            <button
              onClick={handleTrain}
              disabled={isTraining || !trainingRepoId}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {isTraining ? 'Entraînement...' : 'Lancer l\'entraînement'}
            </button>
            {trainingStatus && (
              <span className={`text-sm ${trainingStatus.includes('Erreur') ? 'text-red-500' : 'text-green-600'}`}>
                {trainingStatus}
              </span>
            )}
          </div>
        </UiCard>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
          <div className="text-xs text-slate-500 dark:text-slate-400">Total Modèles</div>
          <div className="text-2xl font-bold text-slate-900 dark:text-slate-50">{models.length}</div>
        </div>
        <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
          <div className="text-xs text-slate-500 dark:text-slate-400">Modèles Actifs</div>
          <div className="text-2xl font-bold text-green-600 dark:text-green-400">
            {models.filter(m => m.is_active !== false).length}
          </div>
        </div>
        <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
          <div className="text-xs text-slate-500 dark:text-slate-400">Accuracy Moyenne</div>
          <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
            {models.length > 0
              ? (models.reduce((sum, m) => sum + (m.metrics?.accuracy || 0), 0) / models.length * 100).toFixed(1) + '%'
              : 'N/A'}
          </div>
        </div>
        <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
          <div className="text-xs text-slate-500 dark:text-slate-400">Meilleur F1-Score</div>
          <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
            {models.length > 0
              ? Math.max(...models.map(m => m.metrics?.f1_score || 0)).toFixed(3)
              : 'N/A'}
          </div>
        </div>
      </div>

      <UiCard>
        <div className="p-4">
          <h2 className="text-lg font-semibold mb-4 text-slate-900 dark:text-slate-50">
            Liste des Modèles
          </h2>

          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
            </div>
          ) : error ? (
            <div className="p-4 text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg">
              <p className="font-semibold mb-2">Erreur: {error}</p>
              <button
                onClick={fetchModels}
                className="mt-2 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Réessayer
              </button>
            </div>
          ) : models.length === 0 ? (
            <div className="p-8 text-center">
              <div className="text-4xl mb-4">🤖</div>
              <p className="text-gray-500 dark:text-gray-400 mb-2">Aucun modèle trouvé</p>
              <p className="text-sm text-gray-400 dark:text-gray-500">
                Utilisez le ML Pipeline pour entraîner votre premier modèle.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-100 dark:bg-slate-800">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium">Model ID</th>
                    <th className="px-4 py-3 text-left font-medium">Type</th>
                    <th className="px-4 py-3 text-left font-medium">Statut</th>
                    <th className="px-4 py-3 text-left font-medium">Accuracy</th>
                    <th className="px-4 py-3 text-left font-medium">Precision</th>
                    <th className="px-4 py-3 text-left font-medium">Recall</th>
                    <th className="px-4 py-3 text-left font-medium">F1-Score</th>
                    <th className="px-4 py-3 text-left font-medium">Date</th>
                    <th className="px-4 py-3 text-left font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                  {models.map((model) => (
                    <tr key={model.model_id} className="hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors">
                      <td className="px-4 py-3 font-mono text-xs">
                        {model.model_id.substring(0, 20)}...
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-800 dark:bg-indigo-900 dark:text-indigo-200">
                          {model.model_type || 'N/A'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {getStatusBadge(model)}
                      </td>
                      <td className={`px-4 py-3 font-semibold ${getAccuracyColor(model.metrics?.accuracy)}`}>
                        {model.metrics?.accuracy !== undefined
                          ? (model.metrics.accuracy * 100).toFixed(1) + '%'
                          : 'N/A'}
                      </td>
                      <td className="px-4 py-3">
                        {model.metrics?.precision !== undefined
                          ? (model.metrics.precision * 100).toFixed(1) + '%'
                          : 'N/A'}
                      </td>
                      <td className="px-4 py-3">
                        {model.metrics?.recall !== undefined
                          ? (model.metrics.recall * 100).toFixed(1) + '%'
                          : 'N/A'}
                      </td>
                      <td className="px-4 py-3 font-medium">
                        {model.metrics?.f1_score !== undefined
                          ? model.metrics.f1_score.toFixed(3)
                          : 'N/A'}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500">
                        {model.created_at
                          ? new Date(model.created_at).toLocaleDateString()
                          : 'N/A'}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {/* Toggle Active */}
                          <button
                            onClick={() => toggleModelStatus(model.model_id, model.is_active !== false)}
                            disabled={actionLoading === model.model_id}
                            className={`px-2 py-1 text-xs rounded transition-colors ${model.is_active !== false
                              ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200 dark:bg-yellow-900 dark:text-yellow-300'
                              : 'bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900 dark:text-green-300'
                              }`}
                            title={model.is_active !== false ? 'Désactiver' : 'Activer'}
                          >
                            {model.is_active !== false ? 'Désactiver' : 'Activer'}
                          </button>

                          {/* Set as Best */}
                          {!model.is_best && (
                            <button
                              onClick={() => setAsBestModel(model.model_id)}
                              disabled={actionLoading === model.model_id}
                              className="px-2 py-1 text-xs rounded bg-purple-100 text-purple-700 hover:bg-purple-200 dark:bg-purple-900 dark:text-purple-300 transition-colors"
                              title="Définir comme meilleur modèle"
                            >
                              ★
                            </button>
                          )}

                          {/* Delete */}
                          <button
                            onClick={() => deleteModel(model.model_id)}
                            disabled={actionLoading === model.model_id}
                            className="px-2 py-1 text-xs rounded bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900 dark:text-red-300 transition-colors"
                            title="Supprimer"
                          >
                            ✕
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </UiCard>

      {/* Légende */}
      <UiCard>
        <div className="p-4">
          <h3 className="text-sm font-semibold mb-3 text-slate-900 dark:text-slate-50">
            Légende des Métriques
          </h3>
          <div className="grid md:grid-cols-4 gap-4 text-xs text-slate-600 dark:text-slate-400">
            <div>
              <span className="font-medium">Accuracy</span>: Pourcentage de prédictions correctes.
            </div>
            <div>
              <span className="font-medium">Precision</span>: Parmi les fichiers prédits risqués, combien le sont vraiment.
            </div>
            <div>
              <span className="font-medium">Recall</span>: Parmi les fichiers réellement risqués, combien ont été détectés.
            </div>
            <div>
              <span className="font-medium">F1-Score</span>: Moyenne harmonique de Precision et Recall.
            </div>
          </div>
        </div>
      </UiCard>
    </div>
  )
}
