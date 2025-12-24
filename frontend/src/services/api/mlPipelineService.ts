import { mlServiceClient } from './client'
import { pretraitementClient } from './client'
import { priorisationClient } from './client'
import { backendClient } from './client'

export type AutoTuneRequest = {
  dataset_id: number
  repo_id?: number
  model_family?: 'auto' | 'xgb' | 'lgbm' | 'rf' | 'logreg' | 'ensemble'
  target_metric?: 'roc_auc' | 'pr_auc' | 'f1' | 'accuracy'
  threshold_metric?: 'f1' | 'accuracy'
  n_trials?: number
  use_temporal_cv?: boolean
}

export type AutoTuneResponse = {
  model_id: string
  model_type: string
  metrics: {
    accuracy: number
    precision: number
    recall: number
    f1: number
    roc_auc?: number
    pr_auc?: number
  }
  optimal_threshold: number
  best_params: Record<string, any>
  diagnosis: any
  mlflow_run_id?: string
}

export type PipelineStep = {
  step: string
  status: 'pending' | 'running' | 'success' | 'error'
  message?: string
  data?: any
}

export type CompletePipelineRequest = {
  repo_id: number
  balancing_strategy?: 'none' | 'smote' | 'cost_sensitive'
  model_family?: 'auto' | 'ensemble' | 'xgb' | 'lgbm' | 'rf'
  target_metric?: 'roc_auc' | 'pr_auc' | 'f1' | 'accuracy'
  n_trials?: number
}

export type CompletePipelineResponse = {
  collection: CollectionResult
  features: FeatureGenerationResponse
  training: AutoTuneResponse
  prioritization?: PrioritizationResponse
}

// Import types from other services
import type { CollectionResult } from './repoService'
import type { FeatureGenerationResponse } from './pretraitementService'
import type { PrioritizationResponse } from './priorisationService'

/**
 * Execute complete pipeline: Collect → Features → Train → Prioritize
 * @param onProgress Optional callback to report progress in real-time
 */
export async function executeCompletePipeline(
  request: CompletePipelineRequest,
  onProgress?: (steps: PipelineStep[]) => void
): Promise<CompletePipelineResponse> {
  const steps: PipelineStep[] = []

  const updateProgress = (newStep: PipelineStep) => {
    const existingIndex = steps.findIndex(s => s.step === newStep.step)
    if (existingIndex !== -1) {
      steps[existingIndex] = newStep
    } else {
      steps.push(newStep)
    }
    onProgress?.(steps.map(s => ({ ...s }))) // Notify with a copy
  }

  try {
    // Step 1: Collect data
    updateProgress({ step: 'collection', status: 'running', message: 'Collecting repository data...' })
    const collection = await backendClient.post<CollectionResult>(
      `/api/repos/${request.repo_id}/collect`
    )
    updateProgress({ step: 'collection', status: 'success', data: collection.data, message: `Collected ${collection.data.commits_stored} commits` })

    // Step 2: Generate features
    updateProgress({ step: 'features', status: 'running', message: 'Generating features...' })
    const features = await pretraitementClient.post<FeatureGenerationResponse>(
      '/features/generate',
      {
        repo_id: request.repo_id,
        balancing_strategy: request.balancing_strategy || 'smote',
        use_temporal_split: true
      }
    )
    updateProgress({ step: 'features', status: 'success', data: features.data, message: `Generated ${features.data.n_features} features` })

    // Step 3: Train model
    updateProgress({ step: 'training', status: 'running', message: 'Training ML model (this may take several minutes)...' })
    const training = await mlServiceClient.post<AutoTuneResponse>(
      '/train/auto',
      {
        dataset_id: features.data.dataset_id,
        repo_id: request.repo_id,
        model_family: request.model_family || 'ensemble',
        target_metric: request.target_metric || 'roc_auc',
        n_trials: request.n_trials || 30,
        use_temporal_cv: true
      }
    )
    updateProgress({ step: 'training', status: 'success', data: training.data, message: `Model trained: ${(training.data.metrics.accuracy * 100).toFixed(1)}% accuracy` })

    // Step 4: Get predictions and prioritize
    updateProgress({ step: 'prioritization', status: 'running', message: 'Generating prioritized plan...' })
    try {
      // Get predictions for files
      // Note: We need to get the test dataset and make predictions
      // For now, we'll create example items based on the model metrics
      // In production, we would:
      // 1. Fetch the test dataset from pretraitement-features
      // 2. Make predictions using the trained model
      // 3. Convert to prioritization items

      // Simplified: Create example items for demonstration
      // In production, this would come from actual predictions
      const exampleItems = Array.from({ length: 10 }, (_, idx) => ({
        id: `file_${idx + 1}`,
        risk: Math.random() * 0.5 + 0.3, // Random risk between 0.3 and 0.8
        effort: Math.floor(Math.random() * 200) + 50, // Random effort between 50 and 250
        criticite: 1.0 + Math.random() * 0.5, // Random criticité between 1.0 and 1.5
        module: idx % 3 === 0 ? 'core' : idx % 3 === 1 ? 'api' : 'utils',
        risk_confidence: training.data.metrics.accuracy || 0.7
      }))

      const items = exampleItems

      const prioritization = await priorisationClient.post<PrioritizationResponse>(
        '/prioritize',
        {
          repo_id: request.repo_id,
          items,
          budget: 1000,
          weights: {
            risk: 1.0,
            crit: 0.5
          }
        }
      )
      updateProgress({ step: 'prioritization', status: 'success', data: prioritization.data, message: `Selected ${prioritization.data.summary.items_selected} items` })

      return {
        collection: collection.data,
        features: features.data,
        training: training.data,
        prioritization: prioritization.data
      }
    } catch (priorError) {
      updateProgress({ step: 'prioritization', status: 'error', message: String(priorError) })
      // Return without prioritization
      return {
        collection: collection.data,
        features: features.data,
        training: training.data
      }
    }

  } catch (error: any) {
    const failedStep = steps.find(s => s.status === 'running')
    if (failedStep) {
      updateProgress({
        step: failedStep.step,
        status: 'error',
        message: error.message || String(error)
      })
    }
    throw error
  }
}

/**
 * Train model with auto-tuning
 */
export async function trainModel(request: AutoTuneRequest): Promise<AutoTuneResponse> {
  const { data } = await mlServiceClient.post<AutoTuneResponse>('/train/auto', request)
  return data
}

/**
 * Get predictions for a dataset
 */
export async function getPredictions(
  datasetId: number,
  modelId?: string
): Promise<{
  predictions: Array<{ id: string; risk: number; probability: number }>
  model_id: string
}> {
  const { data } = await mlServiceClient.post('/predict', {
    dataset_id: datasetId,
    model_id: modelId
  })
  return data
}

