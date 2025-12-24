import { apiClient } from './client'

// ---- Types ----

export type PrioritisationItem = {
  id: string
  type: 'test' | 'defect' | 'class' | 'module'
  score: number
  reason?: string
}

export type PrioritiseRequest = {
  repoId: string
  limit?: number
  signals?: string[]
}

export type PrioritiseResponse = {
  repoId: string
  generatedAt: string
  items: PrioritisationItem[]
}

// ---- Service functions ----

export async function prioritiseWork(
  payload: PrioritiseRequest,
): Promise<PrioritiseResponse> {
  const { data } = await apiClient.post<PrioritiseResponse>('/prioritize', payload)
  return data
}


