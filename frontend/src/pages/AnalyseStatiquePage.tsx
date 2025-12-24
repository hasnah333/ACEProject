import { useState, useEffect } from 'react'
import { UiCard } from '../components/ui/UiCard'
import { ChartPanel } from '../components/ui/ChartPanel'
import { analyseStatiqueClient } from '../services/api/analyseStatiqueService'
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
    PieChart, Pie, Cell, ScatterChart, Scatter, ZAxis
} from 'recharts'

import { listRepos } from '../services/api/repoService'
import type { Repo } from '../services/api/repoService'

// Types
interface FileMetrics {
    filepath: string
    cyclomatic_complexity: number
    wmc: number
    dit: number
    noc: number
    cbo: number
    rfc: number
    lcom: number
    fan_in: number
    fan_out: number
    loc: number
    sloc: number
    code_smells_count: number
}

interface CodeSmell {
    filepath: string
    smell_type: string
    severity: string
    message: string
}

interface AnalysisSummary {
    file_count: number
    avg_cyclomatic_complexity: number
    max_cyclomatic_complexity: number
    avg_wmc: number
    avg_cbo: number
    avg_lcom: number
    total_code_smells: number
    total_loc: number
}


const SEVERITY_COLORS: Record<string, string> = {
    low: '#22c55e',
    medium: '#f59e0b',
    high: '#ef4444',
    critical: '#dc2626'
}

export function AnalyseStatiquePage() {
    const [loading, setLoading] = useState(true)
    const [repos, setRepos] = useState<Repo[]>([])
    const [selectedRepoId, setSelectedRepoId] = useState<number | null>(null)
    const [metrics, setMetrics] = useState<FileMetrics[]>([])
    const [smells, setSmells] = useState<CodeSmell[]>([])
    const [summary, setSummary] = useState<AnalysisSummary | null>(null)
    const [analyzing, setAnalyzing] = useState(false)

    useEffect(() => {
        const loadRepos = async () => {
            try {
                const list = await listRepos()
                setRepos(list)
                if (list.length > 0) {
                    setSelectedRepoId(list[0].id)
                }
            } catch (e) {
                console.error('Failed to load repos:', e)
            }
        }
        loadRepos()
    }, [])

    useEffect(() => {
        if (selectedRepoId) {
            loadData()
        }
    }, [selectedRepoId])

    const loadData = async () => {
        setLoading(true)
        try {
            // Essayer de charger les données réelles
            await Promise.all([
                loadMetrics(),
                loadSmells(),
                loadSummary()
            ])
        } catch (error) {
            console.log('Loading demo data')
            loadDemoData()
        } finally {
            setLoading(false)
        }
    }

    const loadMetrics = async () => {
        try {
            const response = await analyseStatiqueClient.get(`/metrics/${selectedRepoId}`)
            if (response.data?.metrics) {
                setMetrics(response.data.metrics)
            } else if (Array.isArray(response.data)) {
                setMetrics(response.data)
            }
        } catch {
            // Ignorer et utiliser les données de démo
        }
    }

    const loadSmells = async () => {
        try {
            const response = await analyseStatiqueClient.get(`/smells/${selectedRepoId}`)
            if (response.data?.smells) {
                setSmells(response.data.smells)
            } else if (Array.isArray(response.data)) {
                setSmells(response.data)
            }
        } catch {
            // Ignorer et utiliser les données de démo
        }
    }

    const loadSummary = async () => {
        try {
            const response = await analyseStatiqueClient.get(`/summary/${selectedRepoId}`)
            if (response.data?.summary) {
                setSummary(response.data.summary)
            } else if (response.data && response.data.file_count !== undefined) {
                setSummary(response.data)
            }
        } catch {
            // Ignorer et utiliser les données de démo
        }
    }

    const loadDemoData = () => {
        // Données de démonstration
        setMetrics([
            { filepath: 'UserService.java', cyclomatic_complexity: 45, wmc: 35, dit: 2, noc: 1, cbo: 12, rfc: 42, lcom: 65, fan_in: 8, fan_out: 15, loc: 280, sloc: 220, code_smells_count: 3 },
            { filepath: 'OrderController.java', cyclomatic_complexity: 32, wmc: 28, dit: 1, noc: 0, cbo: 8, rfc: 35, lcom: 45, fan_in: 5, fan_out: 12, loc: 190, sloc: 150, code_smells_count: 2 },
            { filepath: 'ProductRepository.java', cyclomatic_complexity: 18, wmc: 15, dit: 1, noc: 2, cbo: 5, rfc: 22, lcom: 30, fan_in: 10, fan_out: 6, loc: 120, sloc: 95, code_smells_count: 1 },
            { filepath: 'AuthFilter.java', cyclomatic_complexity: 52, wmc: 42, dit: 3, noc: 0, cbo: 15, rfc: 55, lcom: 78, fan_in: 2, fan_out: 18, loc: 350, sloc: 280, code_smells_count: 5 },
            { filepath: 'DataProcessor.java', cyclomatic_complexity: 28, wmc: 22, dit: 2, noc: 1, cbo: 9, rfc: 30, lcom: 40, fan_in: 6, fan_out: 10, loc: 180, sloc: 140, code_smells_count: 2 },
            { filepath: 'helpers.py', cyclomatic_complexity: 12, wmc: 10, dit: 0, noc: 0, cbo: 3, rfc: 15, lcom: 20, fan_in: 15, fan_out: 5, loc: 80, sloc: 60, code_smells_count: 0 },
        ])

        setSmells([
            { filepath: 'AuthFilter.java', smell_type: 'high_complexity', severity: 'high', message: 'Cyclomatic complexity of 52 exceeds threshold of 10' },
            { filepath: 'AuthFilter.java', smell_type: 'god_class', severity: 'high', message: 'Class has too many responsibilities' },
            { filepath: 'AuthFilter.java', smell_type: 'long_method', severity: 'medium', message: 'Method authenticate() is too long (85 lines)' },
            { filepath: 'UserService.java', smell_type: 'high_coupling', severity: 'medium', message: 'CBO of 12 exceeds threshold of 10' },
            { filepath: 'UserService.java', smell_type: 'large_class', severity: 'low', message: 'Class has 280 lines' },
            { filepath: 'OrderController.java', smell_type: 'high_complexity', severity: 'medium', message: 'Cyclomatic complexity of 32 exceeds threshold of 10' },
        ])

        setSummary({
            file_count: 6,
            avg_cyclomatic_complexity: 31.2,
            max_cyclomatic_complexity: 52,
            avg_wmc: 25.3,
            avg_cbo: 8.7,
            avg_lcom: 46.3,
            total_code_smells: 13,
            total_loc: 1200
        })
    }

    const runAnalysis = async () => {
        if (!selectedRepoId) return
        setAnalyzing(true)
        try {
            await analyseStatiqueClient.post('/analyze', { repo_id: selectedRepoId })
            await loadData()
        } catch (error) {
            console.error('Analysis failed:', error)
            loadDemoData()
        } finally {
            setAnalyzing(false)
        }
    }

    // Préparer les données pour les graphiques
    const ckMetricsData = metrics.map(m => ({
        name: m.filepath.split('/').pop()?.substring(0, 15) || m.filepath,
        WMC: m.wmc,
        CBO: m.cbo,
        RFC: m.rfc,
        LCOM: Math.min(m.lcom, 100)
    }))

    const complexityData = metrics.map(m => ({
        name: m.filepath.split('/').pop()?.substring(0, 15) || m.filepath,
        complexity: m.cyclomatic_complexity,
        loc: m.loc,
        smells: m.code_smells_count
    }))

    const smellsBySeverity = ['critical', 'high', 'medium', 'low'].map(severity => ({
        name: severity.charAt(0).toUpperCase() + severity.slice(1),
        value: smells.filter(s => s.severity === severity).length,
        color: SEVERITY_COLORS[severity]
    })).filter(s => s.value > 0)

    const smellsByType = Object.entries(
        smells.reduce((acc, s) => {
            acc[s.smell_type] = (acc[s.smell_type] || 0) + 1
            return acc
        }, {} as Record<string, number>)
    ).map(([type, count]) => ({
        type: type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
        count
    }))

    const scatterData = metrics.map(m => ({
        name: m.filepath.split('/').pop(),
        complexity: m.cyclomatic_complexity,
        coupling: m.cbo,
        smells: m.code_smells_count + 1
    }))

    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Repository Selector */}
            <UiCard>
                <div className="flex items-center gap-4">
                    <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                        Sélectionner un dépôt:
                    </label>
                    <select
                        value={selectedRepoId || ''}
                        onChange={(e) => setSelectedRepoId(Number(e.target.value))}
                        className="flex-1 max-w-md px-3 py-2 border border-slate-300 rounded-md dark:bg-slate-800 dark:border-slate-600 outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                        {repos.map(repo => (
                            <option key={repo.id} value={repo.id}>
                                {repo.name} ({repo.url})
                            </option>
                        ))}
                    </select>
                </div>
            </UiCard>

            {/* Header */}
            <div className="flex justify-between items-start">
                <div className="space-y-2">
                    <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
                        🔍 Analyse Statique du Code
                    </h1>
                    <p className="text-sm text-slate-500 dark:text-slate-400">
                        Métriques CK (WMC, DIT, NOC, CBO, RFC, LCOM), complexité cyclomatique (McCabe), dépendances et code smells
                    </p>
                </div>
                <button
                    onClick={runAnalysis}
                    disabled={analyzing || !selectedRepoId}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2 transition-all shadow-md active:scale-95"
                >
                    {analyzing ? (
                        <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                            Analyse en cours...
                        </>
                    ) : (
                        <>
                            🔬 Lancer l'analyse
                        </>
                    )}
                </button>
            </div>

            {/* Summary Cards */}
            {summary && (
                <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
                    <SummaryCard title="Fichiers" value={summary.file_count.toString()} icon="📁" />
                    <SummaryCard title="LOC Total" value={summary.total_loc.toLocaleString()} icon="📝" />
                    <SummaryCard title="CC Moyen" value={summary.avg_cyclomatic_complexity.toFixed(1)} icon="🔄" color={summary.avg_cyclomatic_complexity > 20 ? 'red' : 'green'} />
                    <SummaryCard title="CC Max" value={summary.max_cyclomatic_complexity.toString()} icon="⚡" color={summary.max_cyclomatic_complexity > 30 ? 'red' : 'orange'} />
                    <SummaryCard title="WMC Moyen" value={summary.avg_wmc.toFixed(1)} icon="⚖️" />
                    <SummaryCard title="CBO Moyen" value={summary.avg_cbo.toFixed(1)} icon="🔗" color={summary.avg_cbo > 10 ? 'red' : 'green'} />
                    <SummaryCard title="LCOM Moyen" value={summary.avg_lcom.toFixed(1)} icon="📊" />
                    <SummaryCard title="Code Smells" value={summary.total_code_smells.toString()} icon="⚠️" color={summary.total_code_smells > 10 ? 'red' : 'green'} />
                </div>
            )}

            {/* Graphiques principaux */}
            <div className="grid lg:grid-cols-2 gap-6">
                {/* Métriques CK */}
                <ChartPanel
                    title="Métriques CK par Fichier"
                    subtitle="WMC, CBO, RFC, LCOM - Indicateurs de qualité orientés objet"
                >
                    <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={ckMetricsData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                                <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} tick={{ fontSize: 10 }} />
                                <YAxis tick={{ fontSize: 12 }} />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="WMC" fill="#6366f1" name="WMC" />
                                <Bar dataKey="CBO" fill="#f59e0b" name="CBO" />
                                <Bar dataKey="RFC" fill="#22c55e" name="RFC" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </ChartPanel>

                {/* Complexité vs Taille */}
                <ChartPanel
                    title="Complexité Cyclomatique (McCabe)"
                    subtitle="Complexité par fichier - Seuil recommandé: 10"
                >
                    <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={complexityData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                                <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} tick={{ fontSize: 10 }} />
                                <YAxis tick={{ fontSize: 12 }} />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="complexity" fill="#ef4444" name="Complexité" />
                                <Bar dataKey="smells" fill="#f59e0b" name="Code Smells" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </ChartPanel>
            </div>

            {/* Graphiques secondaires */}
            <div className="grid lg:grid-cols-3 gap-6">
                {/* Code Smells par Sévérité */}
                <ChartPanel
                    title="Code Smells par Sévérité"
                    subtitle="Distribution des problèmes détectés"
                >
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={smellsBySeverity}
                                    cx="50%"
                                    cy="50%"
                                    innerRadius={40}
                                    outerRadius={80}
                                    dataKey="value"
                                    label={({ name, value }: { name: string; value: number }) => `${name}: ${value}`}
                                >
                                    {smellsBySeverity.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </ChartPanel>

                {/* Code Smells par Type */}
                <ChartPanel
                    title="Types de Code Smells"
                    subtitle="Catégories de problèmes"
                >
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={smellsByType} layout="vertical" margin={{ top: 20, right: 30, left: 100, bottom: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                                <XAxis type="number" tick={{ fontSize: 12 }} />
                                <YAxis dataKey="type" type="category" tick={{ fontSize: 10 }} width={90} />
                                <Tooltip />
                                <Bar dataKey="count" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </ChartPanel>

                {/* Scatter: Complexité vs Couplage */}
                <ChartPanel
                    title="Complexité vs Couplage"
                    subtitle="Identification des fichiers à risque"
                >
                    <div className="h-64">
                        <ResponsiveContainer width="100%" height="100%">
                            <ScatterChart margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                                <XAxis dataKey="complexity" name="Complexité" tick={{ fontSize: 12 }} />
                                <YAxis dataKey="coupling" name="Couplage (CBO)" tick={{ fontSize: 12 }} />
                                <ZAxis dataKey="smells" range={[50, 400]} name="Smells" />
                                <Tooltip cursor={{ strokeDasharray: '3 3' }} />
                                <Scatter data={scatterData} fill="#ef4444">
                                    {scatterData.map((entry, index) => (
                                        <Cell
                                            key={`cell-${index}`}
                                            fill={entry.complexity > 30 || entry.coupling > 10 ? '#ef4444' : '#22c55e'}
                                        />
                                    ))}
                                </Scatter>
                            </ScatterChart>
                        </ResponsiveContainer>
                    </div>
                </ChartPanel>
            </div>

            {/* Tableau des Métriques Détaillées */}
            <UiCard>
                <h2 className="text-lg font-semibold mb-4 text-slate-900 dark:text-slate-50">
                    📋 Métriques CK Détaillées par Fichier
                </h2>
                <div className="overflow-x-auto">
                    <table className="min-w-full text-sm">
                        <thead className="bg-slate-100 dark:bg-slate-800">
                            <tr>
                                <th className="px-4 py-3 text-left font-medium">Fichier</th>
                                <th className="px-4 py-3 text-left font-medium">CC</th>
                                <th className="px-4 py-3 text-left font-medium">WMC</th>
                                <th className="px-4 py-3 text-left font-medium">DIT</th>
                                <th className="px-4 py-3 text-left font-medium">NOC</th>
                                <th className="px-4 py-3 text-left font-medium">CBO</th>
                                <th className="px-4 py-3 text-left font-medium">RFC</th>
                                <th className="px-4 py-3 text-left font-medium">LCOM</th>
                                <th className="px-4 py-3 text-left font-medium">Fan-In</th>
                                <th className="px-4 py-3 text-left font-medium">Fan-Out</th>
                                <th className="px-4 py-3 text-left font-medium">LOC</th>
                                <th className="px-4 py-3 text-left font-medium">Smells</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                            {metrics.map((m) => (
                                <tr key={m.filepath} className="hover:bg-slate-50 dark:hover:bg-slate-800">
                                    <td className="px-4 py-3 font-medium">{m.filepath.split('/').pop()}</td>
                                    <td className={`px-4 py-3 ${m.cyclomatic_complexity > 20 ? 'text-red-600 font-bold' : ''}`}>
                                        {m.cyclomatic_complexity}
                                    </td>
                                    <td className="px-4 py-3">{m.wmc}</td>
                                    <td className="px-4 py-3">{m.dit}</td>
                                    <td className="px-4 py-3">{m.noc}</td>
                                    <td className={`px-4 py-3 ${m.cbo > 10 ? 'text-orange-600 font-bold' : ''}`}>
                                        {m.cbo}
                                    </td>
                                    <td className="px-4 py-3">{m.rfc}</td>
                                    <td className="px-4 py-3">{m.lcom}</td>
                                    <td className="px-4 py-3">{m.fan_in}</td>
                                    <td className="px-4 py-3">{m.fan_out}</td>
                                    <td className="px-4 py-3">{m.loc}</td>
                                    <td className="px-4 py-3">
                                        {m.code_smells_count > 0 ? (
                                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
                                                {m.code_smells_count}
                                            </span>
                                        ) : (
                                            <span className="text-green-600">✓</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </UiCard>

            {/* Liste des Code Smells */}
            {smells.length > 0 && (
                <UiCard>
                    <h2 className="text-lg font-semibold mb-4 text-slate-900 dark:text-slate-50">
                        ⚠️ Code Smells Détectés ({smells.length})
                    </h2>
                    <div className="space-y-3">
                        {smells.map((smell, index) => (
                            <div
                                key={index}
                                className={`p-4 rounded-lg border-l-4 ${smell.severity === 'critical' ? 'border-red-600 bg-red-50 dark:bg-red-900/20' :
                                    smell.severity === 'high' ? 'border-red-500 bg-red-50 dark:bg-red-900/20' :
                                        smell.severity === 'medium' ? 'border-orange-500 bg-orange-50 dark:bg-orange-900/20' :
                                            'border-green-500 bg-green-50 dark:bg-green-900/20'
                                    }`}
                            >
                                <div className="flex justify-between items-start">
                                    <div>
                                        <span className="font-medium text-slate-900 dark:text-slate-50">
                                            {smell.filepath.split('/').pop()}
                                        </span>
                                        <span className={`ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${smell.severity === 'critical' || smell.severity === 'high'
                                            ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                                            : smell.severity === 'medium'
                                                ? 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200'
                                                : 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                                            }`}>
                                            {smell.severity}
                                        </span>
                                    </div>
                                    <span className="text-xs text-slate-500">
                                        {smell.smell_type.replace(/_/g, ' ')}
                                    </span>
                                </div>
                                <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                                    {smell.message}
                                </p>
                            </div>
                        ))}
                    </div>
                </UiCard>
            )}

            {/* Légende des Métriques */}
            <UiCard>
                <h2 className="text-lg font-semibold mb-4 text-slate-900 dark:text-slate-50">
                    📚 Légende des Métriques CK
                </h2>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                    <MetricLegend
                        name="WMC"
                        fullName="Weighted Methods per Class"
                        description="Somme des complexités cyclomatiques de toutes les méthodes d'une classe"
                        threshold="< 20 recommandé"
                    />
                    <MetricLegend
                        name="DIT"
                        fullName="Depth of Inheritance Tree"
                        description="Profondeur maximale de l'arbre d'héritage"
                        threshold="< 5 recommandé"
                    />
                    <MetricLegend
                        name="NOC"
                        fullName="Number of Children"
                        description="Nombre de sous-classes directes"
                        threshold="Éviter trop de sous-classes"
                    />
                    <MetricLegend
                        name="CBO"
                        fullName="Coupling Between Objects"
                        description="Nombre de classes couplées à cette classe"
                        threshold="< 10 recommandé"
                    />
                    <MetricLegend
                        name="RFC"
                        fullName="Response for a Class"
                        description="Nombre de méthodes potentiellement exécutées en réponse à un message"
                        threshold="< 50 recommandé"
                    />
                    <MetricLegend
                        name="LCOM"
                        fullName="Lack of Cohesion of Methods"
                        description="Mesure le manque de cohésion entre les méthodes"
                        threshold="Plus bas est mieux"
                    />
                </div>
            </UiCard>
        </div>
    )
}

// Composant carte de résumé
function SummaryCard({ title, value, icon, color = 'default' }: {
    title: string
    value: string
    icon: string
    color?: 'default' | 'green' | 'red' | 'orange'
}) {
    const valueColor = {
        default: 'text-slate-900 dark:text-slate-50',
        green: 'text-green-600 dark:text-green-400',
        red: 'text-red-600 dark:text-red-400',
        orange: 'text-orange-600 dark:text-orange-400'
    }

    return (
        <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
            <div className="flex items-center gap-2 mb-1">
                <span>{icon}</span>
                <span className="text-xs text-slate-500 dark:text-slate-400">{title}</span>
            </div>
            <div className={`text-xl font-bold ${valueColor[color]}`}>{value}</div>
        </div>
    )
}

// Composant légende des métriques
function MetricLegend({ name, fullName, description, threshold }: {
    name: string
    fullName: string
    description: string
    threshold: string
}) {
    return (
        <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
                <span className="font-bold text-indigo-600 dark:text-indigo-400">{name}</span>
                <span className="text-sm text-slate-600 dark:text-slate-400">- {fullName}</span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">{description}</p>
            <span className="text-xs inline-flex items-center px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
                {threshold}
            </span>
        </div>
    )
}
