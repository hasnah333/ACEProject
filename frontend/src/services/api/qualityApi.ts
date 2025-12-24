import { apiClient } from './client'

export type RepoQuality = {
  id: string
  name: string
  coverage: number
  testsPassing: number
}

export async function fetchRepoQuality(): Promise<RepoQuality[]> {
  const { data } = await apiClient.get<RepoQuality[]>('/quality/repos')
  return data
}


