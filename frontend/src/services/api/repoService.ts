import { backendClient } from './client'

export type Repo = {
  id: number
  name: string
  url: string
  provider: string
}

export type RepoCreateRequest = {
  name: string
  url: string
  provider?: string
}

export type CollectionResult = {
  status: string
  commits_collected: number
  commits_stored: number
  files_stored: number
  issues_collected: number
  issues_stored: number
}

export async function listRepos(): Promise<Repo[]> {
  const { data } = await backendClient.get<Repo[]>('/api/repos')
  return data
}

export async function createRepo(request: RepoCreateRequest): Promise<Repo> {
  const { data } = await backendClient.post<Repo>('/api/repos', request)
  return data
}

export async function collectRepo(repoId: number): Promise<CollectionResult> {
  const { data } = await backendClient.post<CollectionResult>(
    `/api/repos/${repoId}/collect`
  )
  return data
}

export async function getRepo(repoId: number): Promise<Repo> {
  const { data } = await backendClient.get<Repo>(`/api/repos/${repoId}`)
  return data
}
