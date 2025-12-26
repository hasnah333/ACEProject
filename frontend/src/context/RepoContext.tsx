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
  id: string
  name: string
  url: string
  defaultBranch: string
  createdAt: string
}

type RepoContextValue = {
  repos: ConnectedRepo[]
  addRepo: (input: Omit<ConnectedRepo, 'id' | 'createdAt'>, forceId?: string) => ConnectedRepo
  getRepo: (id: string | undefined) => ConnectedRepo | undefined
  refreshRepos: () => Promise<void>
}

const STORAGE_KEY = 'qd_connected_repos'

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

export function RepoProvider({ children }: { children: ReactNode }) {
  const [repos, setRepos] = useState<ConnectedRepo[]>(() => loadInitial())

  const refreshRepos = async () => {
    try {
      const backendRepos = await listRepos()
      const formatted: ConnectedRepo[] = backendRepos.map(r => ({
        id: r.id.toString(),
        name: r.name,
        url: r.url,
        defaultBranch: (r as any).default_branch || 'main',
        createdAt: (r as any).created_at || new Date().toISOString()
      }))
      setRepos(formatted)
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

  const value = useMemo<RepoContextValue>(
    () => ({
      repos,
      addRepo: (input, forceId) => {
        const id = forceId ||
          input.name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-') ||
          `repo-${Date.now()}`
        const repo: ConnectedRepo = {
          id,
          name: input.name.trim() || id,
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
      getRepo: (id) => repos.find((r) => r.id === id),
      refreshRepos,
    }),
    [repos],
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


