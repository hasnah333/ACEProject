import { priorisationClient } from './client'

export type PrioritizationItem = {
  id: string
  risk: number
  effort: number
  criticite?: number
  deps?: string[]
  module?: string
  coverage_gap?: number
  risk_confidence?: number
}

export type PrioritizationRequest = {
  repo_id?: number
  items: PrioritizationItem[]
  budget: number
  weights?: {
    risk?: number
    crit?: number
  }
  sprint_context?: {
    capacity?: number
    time_remaining?: number
    max_items?: number
    mandatory_ids?: string[]
    excluded_ids?: string[]
  }
}

export type PrioritizationPlan = {
  rank: number
  id: string
  module?: string
  selected: boolean
  risk: number
  effort: number
  criticite: number
  priority_score: number
  selection_reason: string
}

export type PrioritizationResponse = {
  summary: {
    budget: number
    effort_selected: number
    items_selected: number
    items_total: number
  }
  plan: PrioritizationPlan[]
}

export async function prioritize(request: PrioritizationRequest): Promise<PrioritizationResponse> {
  const { data } = await priorisationClient.post<PrioritizationResponse>('/prioritize', request)
  return data
}

