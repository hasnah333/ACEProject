import { useEffect, useState } from 'react';
// import API_CONFIG from '../../config/api' // Not used;

interface ConfusionMatrixProps {
  modelId: string;
  title?: string;
}

interface MetricsResponse {
  confusion_matrix?: number[][];
  accuracy?: number;
  precision?: number;
  recall?: number;
  f1?: number;
}

export default function ConfusionMatrix({ modelId, title = 'Matrice de confusion' }: ConfusionMatrixProps) {
  const [confusionMatrix, setConfusionMatrix] = useState<number[][] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);

  useEffect(() => {
    if (modelId) {
      fetchConfusionMatrix();
    }
  }, [modelId]);

  const fetchConfusionMatrix = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Utiliser le proxy Vite pour /ml qui redirige vers ml-service
      const response = await fetch(`/ml/metrics/${modelId}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: MetricsResponse = await response.json();
      
      if (data.confusion_matrix) {
        setConfusionMatrix(data.confusion_matrix);
        setMetrics(data);
      } else {
        throw new Error('Matrice de confusion non trouvée dans les métriques');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors du chargement de la matrice de confusion');
      console.error('Error fetching confusion matrix:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="p-4 text-center">
        <p className="text-gray-500">Chargement de la matrice de confusion...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 text-red-600">
        <p>Erreur: {error}</p>
        <button
          onClick={fetchConfusionMatrix}
          className="mt-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Réessayer
        </button>
      </div>
    );
  }

  if (!confusionMatrix || confusionMatrix.length === 0) {
    return (
      <div className="p-4 text-gray-500">
        <p>Aucune matrice de confusion disponible</p>
      </div>
    );
  }

  // Pour un modèle binaire, les labels sont [0, 1] (pas de défaut, défaut)
  // Pour un modèle multi-classe, on pourrait avoir plus de labels
  const isBinary = confusionMatrix.length === 2;
  const labels = isBinary 
    ? ['Pas de défaut', 'Défaut']
    : confusionMatrix.map((_, i) => `Classe ${i}`);

  // Trouver la valeur maximale pour normaliser les couleurs
  const maxValue = Math.max(...confusionMatrix.flat());

  // Calculer les totaux par ligne et colonne (pour usage futur si besoin)
  // const rowTotals = confusionMatrix.map(row => row.reduce((sum, val) => sum + val, 0));
  // const colTotals = confusionMatrix[0].map((_, colIdx) => 
  //   confusionMatrix.reduce((sum, row) => sum + row[colIdx], 0)
  // );

  return (
    <div className="p-6 bg-white rounded-lg shadow-lg">
      <h3 className="text-2xl font-bold mb-6 text-gray-800">{title}</h3>
      
      {metrics && (
        <div className="mb-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          {metrics.accuracy !== undefined && (
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <div className="text-sm text-gray-600 mb-1">Accuracy</div>
              <div className="text-2xl font-bold text-blue-600">
                {(metrics.accuracy * 100).toFixed(2)}%
              </div>
            </div>
          )}
          {metrics.precision !== undefined && (
            <div className="bg-green-50 p-4 rounded-lg border border-green-200">
              <div className="text-sm text-gray-600 mb-1">Precision</div>
              <div className="text-2xl font-bold text-green-600">
                {(metrics.precision * 100).toFixed(2)}%
              </div>
            </div>
          )}
          {metrics.recall !== undefined && (
            <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
              <div className="text-sm text-gray-600 mb-1">Recall</div>
              <div className="text-2xl font-bold text-purple-600">
                {(metrics.recall * 100).toFixed(2)}%
              </div>
            </div>
          )}
          {metrics.f1 !== undefined && (
            <div className="bg-orange-50 p-4 rounded-lg border border-orange-200">
              <div className="text-sm text-gray-600 mb-1">F1-Score</div>
              <div className="text-2xl font-bold text-orange-600">
                {(metrics.f1 * 100).toFixed(2)}%
              </div>
            </div>
          )}
        </div>
      )}

      <div className="flex gap-6 items-start">
        <div className="flex-1 overflow-x-auto">
          <div className="inline-block min-w-full">
            <table className="border-collapse border border-gray-400 bg-white">
              <thead>
                <tr>
                  <th className="border border-gray-400 p-3 bg-gray-200 font-semibold"></th>
                  <th className="border border-gray-400 p-3 bg-gray-200 text-center font-semibold" colSpan={labels.length}>
                    Prédiction
                  </th>
                </tr>
                <tr>
                  <th className="border border-gray-400 p-3 bg-gray-200 font-semibold"></th>
                  {labels.map((label, idx) => (
                    <th key={idx} className="border border-gray-400 p-3 bg-gray-200 text-center text-sm font-semibold min-w-[100px]">
                      {label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {confusionMatrix.map((row, rowIdx) => (
                  <tr key={rowIdx}>
                    <th className="border border-gray-400 p-3 bg-gray-200 text-center font-semibold">
                      {labels[rowIdx]}
                    </th>
                    {row.map((value, colIdx) => {
                      // Calculer l'intensité de la couleur (0 à 1)
                      const intensity = maxValue > 0 ? value / maxValue : 0;
                      // Utiliser une couleur bleue avec intensité variable (comme dans l'image)
                      // Couleur de base: bleu clair à bleu foncé
                      const blueIntensity = Math.floor(200 + intensity * 55); // De 200 à 255
                      const bgColor = `rgb(59, 130, ${blueIntensity})`;
                      const textColor = intensity > 0.6 ? 'text-white' : 'text-gray-900';
                      
                      return (
                        <td
                          key={colIdx}
                          className={`border border-gray-400 p-4 text-center font-bold text-lg ${textColor}`}
                          style={{ 
                            backgroundColor: bgColor,
                            minWidth: '100px',
                            transition: 'background-color 0.2s'
                          }}
                        >
                          {value}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Barre de couleur verticale (comme dans l'image) */}
        <div className="flex flex-col items-center gap-2">
          <div className="text-sm font-semibold text-gray-700 mb-2">Intensité</div>
          <div className="relative h-64 w-8 bg-gradient-to-b from-blue-200 via-blue-400 to-blue-700 rounded border border-gray-300">
            {/* Marqueurs */}
            <div className="absolute top-0 left-full ml-2 text-xs text-gray-600">1.0</div>
            <div className="absolute top-1/2 left-full ml-2 text-xs text-gray-600">0.5</div>
            <div className="absolute bottom-0 left-full ml-2 text-xs text-gray-600">0.0</div>
          </div>
        </div>
      </div>

      {/* Note explicative */}
      <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-sm text-gray-600">
          <strong>Légende:</strong> La matrice de confusion montre le nombre de prédictions correctes (diagonale) 
          et les erreurs de classification. Les valeurs sur la diagonale représentent les classifications correctes, 
          tandis que les valeurs hors diagonale indiquent les erreurs de prédiction.
        </p>
      </div>
    </div>
  );
}

