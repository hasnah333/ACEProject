import { useState, useEffect } from 'react'
import { executeCompletePipeline } from '../services/api/mlPipelineService'
import type { CompletePipelineRequest } from '../services/api/mlPipelineService'
import { listRepos } from '../services/api/repoService'
import type { Repo } from '../services/api/repoService'
import { UiCard } from '../components/ui/UiCard'

type PipelineStep = {
  step: string
  status: 'pending' | 'running' | 'success' | 'error'
  message?: string
}

export function MLPipelinePage() {
  const [repos, setRepos] = useState<Repo[]>([])
  const [selectedRepoId, setSelectedRepoId] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [steps, setSteps] = useState<PipelineStep[]>([
    { step: 'collection', status: 'pending', message: 'Collect repository data' },
    { step: 'features', status: 'pending', message: 'Generate features' },
    { step: 'training', status: 'pending', message: 'Train ML model' },
    { step: 'prioritization', status: 'pending', message: 'Generate prioritized plan' }
  ])
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  const [config, setConfig] = useState<CompletePipelineRequest>({
    repo_id: 0,
    balancing_strategy: 'smote',
    model_family: 'ensemble',
    target_metric: 'roc_auc',
    n_trials: 30
  })

  useEffect(() => {
    loadRepos()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadRepos = async () => {
    try {
      const reposList = await listRepos()
      setRepos(reposList)
      if (reposList.length > 0 && !selectedRepoId) {
        setSelectedRepoId(reposList[0].id)
        setConfig({ ...config, repo_id: reposList[0].id })
      }
    } catch (err) {
      console.error('Failed to load repos:', err)
    }
  }

  const handleRunPipeline = async () => {
    if (!selectedRepoId) {
      setError('Please select a repository')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    // Reset steps
    setSteps([
      { step: 'collection', status: 'pending', message: 'Collect repository data' },
      { step: 'features', status: 'pending', message: 'Generate features' },
      { step: 'training', status: 'pending', message: 'Train ML model' },
      { step: 'prioritization', status: 'pending', message: 'Generate prioritized plan' }
    ])

    try {
      const request: CompletePipelineRequest = {
        ...config,
        repo_id: selectedRepoId
      }

      // Update steps as pipeline progresses
      const updateStep = (stepName: string, status: PipelineStep['status'], message?: string) => {
        setSteps(prev => prev.map(s =>
          s.step === stepName ? { ...s, status, message } : s
        ))
      }

      updateStep('collection', 'running', 'Collecting repository data...')

      // Execute pipeline with real-time progress updates
      const result = await executeCompletePipeline(request, (progressSteps) => {
        // Update steps in real-time as pipeline progresses
        progressSteps.forEach(progressStep => {
          updateStep(progressStep.step, progressStep.status, progressStep.message)
        })
      })

      setResult(result)
    } catch (err: any) {
      setError(err.message || 'Pipeline execution failed')
      // Mark current step as error
      const currentStep = steps.find(s => s.status === 'running')
      if (currentStep) {
        setSteps(prev => prev.map(s =>
          s.step === currentStep.step ? { ...s, status: 'error', message: err.message } : s
        ))
      }
    } finally {
      setLoading(false)
    }
  }

  const getStepIcon = (status: PipelineStep['status']) => {
    switch (status) {
      case 'success':
        return '✓'
      case 'error':
        return '✗'
      case 'running':
        return '⟳'
      default:
        return '○'
    }
  }

  const getStepColor = (status: PipelineStep['status']) => {
    switch (status) {
      case 'success':
        return 'text-green-600 dark:text-green-400'
      case 'error':
        return 'text-red-600 dark:text-red-400'
      case 'running':
        return 'text-blue-600 dark:text-blue-400 animate-spin'
      default:
        return 'text-slate-400 dark:text-slate-500'
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
          ML Pipeline Complet
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Exécutez le pipeline complet : Collecte → Features → Entraînement → Priorisation
        </p>
      </div>

      <UiCard>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Repository
            </label>
            <select
              value={selectedRepoId || ''}
              onChange={(e) => {
                const id = Number(e.target.value)
                setSelectedRepoId(id)
                setConfig({ ...config, repo_id: id })
              }}
              className="w-full px-3 py-2 border border-slate-300 rounded-md dark:bg-slate-800 dark:border-slate-600"
            >
              <option value="">Select a repository</option>
              {repos.map(repo => (
                <option key={repo.id} value={repo.id}>
                  {repo.name} ({repo.url})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Balancing Strategy
              </label>
              <select
                value={config.balancing_strategy}
                onChange={(e) => setConfig({ ...config, balancing_strategy: e.target.value as 'none' | 'smote' | 'cost_sensitive' })}
                className="w-full px-3 py-2 border border-slate-300 rounded-md dark:bg-slate-800 dark:border-slate-600"
              >
                <option value="none">None</option>
                <option value="smote">SMOTE</option>
                <option value="cost_sensitive">Cost Sensitive</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Model Family
              </label>
              <select
                value={config.model_family}
                onChange={(e) => setConfig({ ...config, model_family: e.target.value as 'auto' | 'ensemble' | 'xgb' | 'lgbm' | 'rf' })}
                className="w-full px-3 py-2 border border-slate-300 rounded-md dark:bg-slate-800 dark:border-slate-600"
              >
                <option value="auto">Auto</option>
                <option value="ensemble">Ensemble</option>
                <option value="xgb">XGBoost</option>
                <option value="lgbm">LightGBM</option>
                <option value="rf">Random Forest</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                Target Metric
              </label>
              <select
                value={config.target_metric}
                onChange={(e) => setConfig({ ...config, target_metric: e.target.value as 'roc_auc' | 'pr_auc' | 'f1' | 'accuracy' })}
                className="w-full px-3 py-2 border border-slate-300 rounded-md dark:bg-slate-800 dark:border-slate-600"
              >
                <option value="roc_auc">ROC-AUC</option>
                <option value="pr_auc">PR-AUC</option>
                <option value="f1">F1 Score</option>
                <option value="accuracy">Accuracy</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                N Trials
              </label>
              <input
                type="number"
                value={config.n_trials}
                onChange={(e) => setConfig({ ...config, n_trials: Number(e.target.value) })}
                min="10"
                max="100"
                className="w-full px-3 py-2 border border-slate-300 rounded-md dark:bg-slate-800 dark:border-slate-600"
              />
            </div>
          </div>

          <button
            onClick={handleRunPipeline}
            disabled={loading || !selectedRepoId}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Running Pipeline...' : 'Run Complete Pipeline'}
          </button>
        </div>
      </UiCard>

      {/* Pipeline Steps */}
      <UiCard>
        <h2 className="text-lg font-semibold mb-4">Pipeline Steps</h2>
        <div className="space-y-3">
          {steps.map((step) => (
            <div key={step.step} className="flex items-center gap-3">
              <span className={`text-xl ${getStepColor(step.status)}`}>
                {getStepIcon(step.status)}
              </span>
              <div className="flex-1">
                <div className="font-medium capitalize">{step.step}</div>
                <div className="text-sm text-slate-500 dark:text-slate-400">
                  {step.message || 'Waiting...'}
                </div>
              </div>
            </div>
          ))}
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
            <h2 className="text-lg font-semibold mb-4">Results</h2>
            <div className="space-y-4">
              <div>
                <h3 className="font-medium mb-2">Collection</h3>
                <div className="text-sm text-slate-600 dark:text-slate-400">
                  Commits: {result.collection?.commits_stored || 0} |
                  Files: {result.collection?.files_stored || 0} |
                  Issues: {result.collection?.issues_stored || 0}
                </div>
              </div>

              <div>
                <h3 className="font-medium mb-2">Features</h3>
                <div className="text-sm text-slate-600 dark:text-slate-400">
                  Dataset ID: {result.features?.dataset_id || 'N/A'} |
                  Features: {result.features?.n_features || 0} |
                  Train: {result.features?.train_samples || 0} |
                  Test: {result.features?.test_samples || 0}
                </div>
              </div>

              <div>
                <h3 className="font-medium mb-2">Trained Model</h3>
                <div className="bg-green-50 dark:bg-green-900/20 p-3 rounded-lg">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-slate-500">Model ID:</span>
                      <span className="ml-2 font-mono text-green-700 dark:text-green-400">
                        {result.training?.model_id || 'N/A'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Type:</span>
                      <span className="ml-2 font-semibold">
                        {result.training?.model_type || 'Unknown'}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Accuracy:</span>
                      <span className="ml-2 font-semibold text-green-600 dark:text-green-400">
                        {((result.training?.metrics?.accuracy || 0) * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">F1 Score:</span>
                      <span className="ml-2 font-semibold">
                        {(result.training?.metrics?.f1 || 0).toFixed(3)}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">Recall:</span>
                      <span className="ml-2 font-semibold">
                        {(result.training?.metrics?.recall || 0).toFixed(3)}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500">ROC-AUC:</span>
                      <span className="ml-2 font-semibold">
                        {(result.training?.metrics?.roc_auc || 0).toFixed(3)}
                      </span>
                    </div>
                  </div>
                </div>
                <a
                  href="/models"
                  className="inline-flex items-center mt-3 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400"
                >
                  Voir tous les modèles →
                </a>
              </div>

              {result.prioritization && (
                <div>
                  <h3 className="font-medium mb-2">Prioritization</h3>
                  <div className="text-sm text-slate-600 dark:text-slate-400">
                    Selected: {result.prioritization.summary?.items_selected || 0} / {result.prioritization.summary?.items_total || 0} |
                    Effort: {result.prioritization.summary?.effort_selected || 0} / {result.prioritization.summary?.budget || 0}
                  </div>
                  <a
                    href="/test-plan"
                    className="inline-flex items-center mt-2 text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400"
                  >
                    Voir le Plan de Tests →
                  </a>
                </div>
              )}
            </div>
          </UiCard>
        </>
      )}
    </div>
  )
}

