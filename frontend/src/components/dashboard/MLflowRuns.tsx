import { useState, useEffect } from 'react';
import API_CONFIG from '../../config/api';
import ConfusionMatrix from './ConfusionMatrix';

interface MLflowRun {
  run_id: string;
  experiment_id: string;
  status: string;
  start_time: number;
  end_time?: number;
  metrics?: Record<string, { value: number; timestamp: number }>;
  params?: Record<string, string>;
  tags?: Record<string, string>;
}


export default function MLflowRuns() {
  const [runs, setRuns] = useState<MLflowRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedModelId, setSelectedModelId] = useState<string | null>(null);

  useEffect(() => {
    fetchMLflowRuns();
  }, []);

  const fetchMLflowRuns = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Utiliser l'API ML Service au lieu de MLflow directement (évite les problèmes CORS)
      const mlServiceUrl = API_CONFIG.ML_SERVICE_URL || 'http://localhost:8003';
      
      // Create AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 seconds
      
      const response = await fetch(`${mlServiceUrl}/api/models/list`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Convertir les modèles en format compatible avec l'affichage
      const models = data.models || [];
      const convertedRuns = models.map((model: any) => ({
        run_id: model.model_id || model.run_id || '',
        experiment_id: 'defect_prediction',
        status: 'FINISHED',
        start_time: model.created_at ? new Date(model.created_at).getTime() : Date.now(),
        metrics: model.metrics ? {
          accuracy: { value: model.metrics.accuracy || 0, timestamp: Date.now() },
          precision: { value: model.metrics.precision || 0, timestamp: Date.now() },
          recall: { value: model.metrics.recall || 0, timestamp: Date.now() },
          f1: { value: model.metrics.f1 || model.metrics.f1_score || 0, timestamp: Date.now() },
          roc_auc: { value: model.metrics.roc_auc || 0, timestamp: Date.now() },
        } : {},
        params: {
          model_type: model.model_type || 'unknown',
          dataset_id: model.dataset_id || '',
        },
        tags: {
          model_id: model.model_id || '',
          model_type: model.model_type || 'unknown',
        },
      }));
      
      setRuns(convertedRuns);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors du chargement des runs');
      console.error('Error fetching models:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-4">
        <p>Chargement des runs MLflow...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-red-600">
        <p>Erreur: {error}</p>
        <button
          onClick={fetchMLflowRuns}
          className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Réessayer
        </button>
      </div>
    );
  }

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-4">Runs MLflow - Experiment: defect_prediction</h2>
      
      {runs.length === 0 ? (
        <p className="text-gray-500">Aucun run trouvé</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full bg-white border border-gray-200">
            <thead>
              <tr className="bg-gray-100">
                <th className="px-4 py-2 text-left border">Run ID</th>
                <th className="px-4 py-2 text-left border">Status</th>
                <th className="px-4 py-2 text-left border">Start Time</th>
                <th className="px-4 py-2 text-left border">Metrics</th>
                <th className="px-4 py-2 text-left border">Model ID</th>
                <th className="px-4 py-2 text-left border">Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.run_id} className="hover:bg-gray-50">
                  <td className="px-4 py-2 border font-mono text-sm">
                    {run.run_id.substring(0, 8)}...
                  </td>
                  <td className="px-4 py-2 border">
                    <span
                      className={`px-2 py-1 rounded text-sm ${
                        run.status === 'FINISHED'
                          ? 'bg-green-100 text-green-800'
                          : run.status === 'FAILED'
                          ? 'bg-red-100 text-red-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {run.status}
                    </span>
                  </td>
                  <td className="px-4 py-2 border">
                    {new Date(run.start_time).toLocaleString()}
                  </td>
                  <td className="px-4 py-2 border">
                    {run.metrics ? (
                      <div className="text-sm">
                        {Object.entries(run.metrics).slice(0, 3).map(([key, value]) => (
                          <div key={key}>
                            <strong>{key}:</strong> {typeof value === 'object' ? value.value : value}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className="text-gray-400">N/A</span>
                    )}
                  </td>
                  <td className="px-4 py-2 border">
                    {run.tags?.model_id || 'N/A'}
                  </td>
                  <td className="px-4 py-2 border">
                    {run.tags?.model_id ? (
                      <button
                        onClick={() => setSelectedModelId(
                          selectedModelId === run.tags?.model_id ? null : run.tags?.model_id || null
                        )}
                        className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
                      >
                        {selectedModelId === run.tags?.model_id ? 'Masquer' : 'Voir'} Matrice
                      </button>
                    ) : (
                      <span className="text-gray-400">N/A</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Afficher la matrice de confusion pour le modèle sélectionné */}
      {selectedModelId && (
        <div className="mt-8 border-t pt-8">
          <ConfusionMatrix 
            modelId={selectedModelId}
            title={`Matrice de confusion - Modèle: ${selectedModelId}`}
          />
        </div>
      )}
      
      <div className="mt-4">
        <a
          href={API_CONFIG.MLFLOW_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:underline"
        >
          Voir dans MLflow UI →
        </a>
      </div>
    </div>
  );
}

