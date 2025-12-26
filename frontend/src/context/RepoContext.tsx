import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { listRepos } from '../services/api/repoService'

export type ConnectedRepo = {
  id: number
  name: string
  url: string
  defaultBranch: string
  createdAt: string
}

type RepoContextValue = {
  repos: ConnectedRepo[]
  selectedRepo: ConnectedRepo | null
  selectedRepoId: number | null
  setSelectedRepoId: (id: number | null) => void
  addRepo: (input: Omit<ConnectedRepo, 'id' | 'createdAt'>, forceId?: number) => ConnectedRepo
  getRepo: (id: string | number | undefined) => ConnectedRepo | undefined
  refreshRepos: () => Promise<void>
}

const STORAGE_KEY = 'qd_connected_repos'
const SELECTED_REPO_KEY = 'qd_selected_repo_id'

const RepoContext = createContext<RepoContextValue | undefined>(undefined)

function loadInitial(): ConnectedRepo[] {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed
  } catch {
    return []
  }
}

function loadSelectedRepoId(): number | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(SELECTED_REPO_KEY)
    if (!raw) return null
    return parseInt(raw, 10)
  } catch {
    return null
  }
}

export function RepoProvider({ children }: { children: ReactNode }) {
  const [repos, setRepos] = useState<ConnectedRepo[]>(() => loadInitial())
  const [selectedRepoId, setSelectedRepoIdState] = useState<number | null>(() => loadSelectedRepoId())

  const setSelectedRepoId = (id: number | null) => {
    setSelectedRepoIdState(id)
    if (typeof window !== 'undefined') {
      if (id !== null) {
        window.localStorage.setItem(SELECTED_REPO_KEY, id.toString())
      } else {
        window.localStorage.removeItem(SELECTED_REPO_KEY)
      }
    }
  }

  const refreshRepos = async () => {
    try {
      const backendRepos = await listRepos()
      const formatted: ConnectedRepo[] = backendRepos.map(r => ({
        id: typeof r.id === 'string' ? parseInt(r.id, 10) : r.id,
        name: r.name,
        url: r.url,
        defaultBranch: (r as any).default_branch || 'main',
        createdAt: (r as any).created_at || new Date().toISOString()
      }))
      setRepos(formatted)

      // Si aucun repo sélectionné et qu'on a des repos, sélectionner le premier
      if (selectedRepoId === null && formatted.length > 0) {
        setSelectedRepoId(formatted[0].id)
      }
    } catch (e) {
      console.error('Failed to sync repos with backend:', e)
    }
  }

  useEffect(() => {
    refreshRepos()
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(repos))
  }, [repos])

  const selectedRepo = useMemo(() => {
    if (selectedRepoId === null) return null
    return repos.find(r => r.id === selectedRepoId) || null
  }, [repos, selectedRepoId])

  const value = useMemo<RepoContextValue>(
    () => ({
      repos,
      selectedRepo,
      selectedRepoId,
      setSelectedRepoId,
      addRepo: (input, forceId) => {
        const id = forceId ?? Date.now()
        const repo: ConnectedRepo = {
          id,
          name: input.name.trim() || `repo-${id}`,
          url: input.url.trim(),
          defaultBranch: input.defaultBranch.trim() || 'main',
          createdAt: new Date().toISOString(),
        }
        setRepos((prev) => {
          const existing = prev.find((r) => r.id === id)
          if (existing) {
            return prev.map((r) => (r.id === id ? repo : r))
          }
          return [...prev, repo]
        })
        return repo
      },
      getRepo: (id) => {
        if (id === undefined) return undefined
        const numId = typeof id === 'string' ? parseInt(id, 10) : id
        return repos.find((r) => r.id === numId)
      },
      refreshRepos,
    }),
    [repos, selectedRepo, selectedRepoId],
  )

  return <RepoContext.Provider value={value}>{children}</RepoContext.Provider>
}

export function useRepos() {
  const ctx = useContext(RepoContext)
  if (!ctx) {
    throw new Error('useRepos must be used within RepoProvider')
  }
  return ctx
}
