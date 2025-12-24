import { UiCard } from '../components/ui/UiCard'
import { useState, useEffect } from 'react'
import { mlServiceClient } from '../services/api/client'

interface Model {
  model_id: string
  model_type: string | null
  created_at: string | null
  dataset_id: string | null
  repo_id: number | null
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

  useEffect(() => {
    fetchModels()
  }, [])

  const fetchModels = async () => {
    try {
      setLoading(true)
      setError(null)
      console.log('Fetching models from /api/models/list...')
      const response = await mlServiceClient.get('/api/models/list')
      console.log('Response received:', response.data)
      
      // Handle different response formats
      let modelsData: Model[] = []
      if (Array.isArray(response.data)) {
        modelsData = response.data
      } else if (response.data && Array.isArray(response.data.models)) {
        modelsData = response.data.models
      } else if (response.data && response.data.model_id) {
        // Single model object
        modelsData = [response.data]
      }
      
      console.log('Parsed models:', modelsData.length)
      setModels(modelsData)
    } catch (err: any) {
      console.error('Error fetching models:', err)
      setError(err.message || 'Erreur lors du chargement des modèles')
      setModels([]) // Set empty array on error
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 p-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
          Machine Learning Models
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Gestion et suivi des modèles ML entraînés via MLflow.
        </p>
      </div>

      <UiCard>
        <div className="p-4">
          <h2 className="text-xl font-semibold mb-4">Liste des Modèles</h2>
          
          {loading ? (
            <div className="p-4">
              <p className="text-gray-500 dark:text-gray-400">Chargement des modèles...</p>
            </div>
          ) : error ? (
            <div className="p-4 text-red-600 dark:text-red-400">
              <p className="font-semibold mb-2">Erreur: {error}</p>
              <button
                onClick={fetchModels}
                className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-700"
              >
                Réessayer
              </button>
            </div>
          ) : models.length === 0 ? (
            <div className="p-4">
              <p className="text-gray-500 dark:text-gray-400">Aucun modèle trouvé</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <p className="mb-4 text-sm text-gray-600 dark:text-gray-400">
                {models.length} modèle(s) trouvé(s)
              </p>
              <table className="min-w-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700">
                <thead>
                  <tr className="bg-gray-100 dark:bg-slate-700">
                    <th className="px-4 py-2 text-left border border-gray-300 dark:border-slate-600">Model ID</th>
                    <th className="px-4 py-2 text-left border border-gray-300 dark:border-slate-600">Type</th>
                    <th className="px-4 py-2 text-left border border-gray-300 dark:border-slate-600">Date</th>
                    <th className="px-4 py-2 text-left border border-gray-300 dark:border-slate-600">Accuracy</th>
                    <th className="px-4 py-2 text-left border border-gray-300 dark:border-slate-600">F1-Score</th>
                    <th className="px-4 py-2 text-left border border-gray-300 dark:border-slate-600">ROC-AUC</th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((model) => (
                    <tr key={model.model_id} className="hover:bg-gray-50 dark:hover:bg-slate-700">
                      <td className="px-4 py-2 border border-gray-300 dark:border-slate-600 font-mono text-sm">
                        {model.model_id}
                      </td>
                      <td className="px-4 py-2 border border-gray-300 dark:border-slate-600">
                        {model.model_type || 'N/A'}
                      </td>
                      <td className="px-4 py-2 border border-gray-300 dark:border-slate-600">
                        {model.created_at
                          ? new Date(model.created_at).toLocaleString()
                          : 'N/A'}
                      </td>
                      <td className="px-4 py-2 border border-gray-300 dark:border-slate-600">
                        {model.metrics?.accuracy !== undefined
                          ? (model.metrics.accuracy * 100).toFixed(2) + '%'
                          : 'N/A'}
                      </td>
                      <td className="px-4 py-2 border border-gray-300 dark:border-slate-600">
                        {model.metrics?.f1_score !== undefined
                          ? model.metrics.f1_score.toFixed(4)
                          : 'N/A'}
                      </td>
                      <td className="px-4 py-2 border border-gray-300 dark:border-slate-600">
                        {model.metrics?.roc_auc !== undefined && model.metrics.roc_auc !== null
                          ? model.metrics.roc_auc.toFixed(4)
                          : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </UiCard>
    </div>
  )
}
