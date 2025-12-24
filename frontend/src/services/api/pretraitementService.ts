import { pretraitementClient } from './client'

export type FeatureGenerationRequest = {
  repo_id: number
  balancing_strategy?: 'none' | 'smote' | 'cost_sensitive'
  use_temporal_split?: boolean
}

export type FeatureGenerationResponse = {
  dataset_id: number
  train_samples: number
  test_samples: number
  n_features: number
  message: string
}

export type DatasetInfo = {
  dataset_id: number
  train_samples: number
  test_samples: number
  n_features: number
  created_at: string
}

export async function generateFeatures(
  request: FeatureGenerationRequest
): Promise<FeatureGenerationResponse> {
  const { data } = await pretraitementClient.post<FeatureGenerationResponse>(
    '/features/generate',
    request
  )
  return data
}

export async function getDatasetInfo(datasetId: number): Promise<DatasetInfo> {
  const { data } = await pretraitementClient.get<DatasetInfo>(
    `/datasets/${datasetId}`
  )
  return data
}

export async function getFeatureSchema(): Promise<{
  features: Array<{ name: string; type: string; description?: string }>
}> {
  const { data } = await pretraitementClient.get('/features/schema')
  return data
}

