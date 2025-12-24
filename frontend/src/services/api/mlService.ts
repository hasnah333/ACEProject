import { mlServiceClient, backendClient } from './client'

// ---- Types ----

export type Model = {
  model_id: string
  model_type: string
  accuracy?: number
  metrics?: {
    accuracy: number
    precision: number
    recall: number
    f1: number
    roc_auc?: number
  }
  created_at?: string
}

export type BestModel = {
  model_id: string
  model_type: string
  accuracy: number
  accuracy_percent: number
  metrics: Record<string, number>
  created_at: string
}

export type Prediction = {
  id: string
  prediction: number
  probability: number
  risk_score: number
  uncertainty?: number
}

export type PredictionResponse = {
  predictions: Prediction[]
  model_id: string
  model_type: string
}

export type ShapValue = {
  feature: string
  importance: number
}

export type ShapExplanation = {
  top_features: ShapValue[]
}

// Via le backend (recommandé - utilise automatiquement le meilleur modèle)
export async function getBestModel(): Promise<BestModel> {
  const { data } = await backendClient.get<{ status: string; model: BestModel }>('/api/ml/best-model')
  return data.model
}

export async function predict(items: Array<{
  id: string
  [key: string]: any
}>, includeUncertainty = false): Promise<PredictionResponse> {
  const { data } = await backendClient.post<{ status: string; predictions: PredictionResponse }>(
    '/api/ml/predict',
    { items, include_uncertainty: includeUncertainty }
  )
  return data.predictions
}

// Directement depuis ML Service
export async function getMLModels(sortByAccuracy = false): Promise<Model[]> {
  const params = sortByAccuracy ? '?sort_by_accuracy=true' : ''
  const { data } = await mlServiceClient.get<{ models: Model[] }>(`/ml/models${params}`)
  return data.models
}

export async function getModelMetrics(modelId: string): Promise<Record<string, number>> {
  const { data } = await mlServiceClient.get<Record<string, number>>(`/ml/metrics/${modelId}`)
  return data
}

export async function getModelAccuracy(modelId: string): Promise<{
  model_id: string
  accuracy: number
  accuracy_percent: number
}> {
  const { data } = await mlServiceClient.get(`/ml/metrics/${modelId}/accuracy`)
  return data
}

export async function getGlobalExplanation(modelId: string, topK = 10): Promise<ShapExplanation> {
  const { data } = await mlServiceClient.get<ShapExplanation>(
    `/ml/explain/global/${modelId}?top_k=${topK}`
  )
  return data
}

export async function getLocalExplanation(
  modelId: string,
  features: Record<string, number>
): Promise<{
  contributions: Array<{
    feature: string
    value: number
    contribution: number
  }>
}> {
  const { data } = await mlServiceClient.post(
    `/ml/explain/local/${modelId}`,
    { features }
  )
  return data
}


