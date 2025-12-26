import { type FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { UiCard } from '../components/ui/UiCard'
import { useRepos } from '../context/RepoContext'
import { createRepo, collectRepo } from '../services/api/repoService'
import { analyseStatiqueClient } from '../services/api/client'

export function ConnectRepoPage() {
  const navigate = useNavigate()
  const { addRepo } = useRepos()
  const [name, setName] = useState('')
  const [url, setUrl] = useState('')
  const [defaultBranch, setDefaultBranch] = useState('main')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return

    setLoading(true)
    setError(null)
    setStatus('Création du dépôt...')

    try {
      // 1. Créer le repo dans le backend
      const repoName = name || url.split('/').slice(-1)[0]?.replace('.git', '') || 'Repository'
      const backendRepo = await createRepo({
        name: repoName,
        url: url,
        provider: 'github'
      })

      // 2. Collecter les fichiers du repo depuis GitHub
      setStatus('Collecte des fichiers depuis GitHub...')
      try {
        const collectResult = await collectRepo(backendRepo.id)
        console.log('Collection result:', collectResult)
        setStatus(`${collectResult.files_stored || 0} fichiers collectés. Analyse en cours...`)
      } catch (collectError) {
        console.warn('Collection failed:', collectError)
        setStatus('Collecte échouée, tentative d\'analyse...')
      }

      // 3. Lancer l'analyse statique automatiquement
      setStatus('Analyse statique en cours...')
      try {
        await analyseStatiqueClient.post('/analyze', { repo_id: backendRepo.id })
        setStatus('Analyse terminée !')
      } catch (analyzeError) {
        console.warn('Analysis failed:', analyzeError)
      }

      // 4. Ajouter au contexte local
      const repo = addRepo({
        name: repoName,
        url,
        defaultBranch,
      }, backendRepo.id)

      navigate(`/repo/${encodeURIComponent(repo.id)}`)
    } catch (err: any) {
      setError(err.message || 'Failed to connect repository')
      console.error('Failed to create repo:', err)
    } finally {
      setLoading(false)
      setStatus('')
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
          Connect a repository
        </h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Connect a GitHub repository to analyze with the ML pipeline. The repository
          will be saved and available in all analysis pages.
        </p>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 p-4 text-sm text-red-800 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      <UiCard>
        <form
          className="space-y-4 text-sm"
          onSubmit={handleSubmit}
        >
          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-600 dark:text-slate-300">
              Repository URL
            </label>
            <input
              type="url"
              required
              placeholder="https://github.com/org/project"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            />
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Enter the full GitHub URL. Commits will be collected automatically.
            </p>
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-600 dark:text-slate-300">
              Display name
            </label>
            <input
              type="text"
              placeholder="web-app"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-xs font-medium text-slate-600 dark:text-slate-300">
              Default branch
            </label>
            <input
              type="text"
              placeholder="main"
              value={defaultBranch}
              onChange={(e) => setDefaultBranch(e.target.value)}
              className="w-40 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition focus:border-primary-500 focus:ring-1 focus:ring-primary-500 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center rounded-md bg-primary-600 px-4 py-2 text-xs font-medium text-white shadow-sm transition hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? 'Connecting...' : 'Connect repo'}
          </button>
          {status && (
            <p className="text-sm text-indigo-600 dark:text-indigo-400 animate-pulse mt-2">
              {status}
            </p>
          )}
        </form>
      </UiCard>
    </div>
  )
}
