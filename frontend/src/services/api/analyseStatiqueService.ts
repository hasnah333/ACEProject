import axios from 'axios'
import API_CONFIG from '../../config/api'

// Client pour l'analyse statique
export const analyseStatiqueClient = axios.create({
    baseURL: API_CONFIG.ANALYSE_STATIQUE_URL,
    timeout: 120_000, // 2 minutes pour l'analyse
})

// Types
export type FileMetrics = {
    filepath: string
    language: string
    cyclomatic_complexity: number
    max_cyclomatic_complexity: number
    avg_cyclomatic_complexity: number
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
    comments: number
    blank_lines: number
    num_methods: number
    num_classes: number
    code_smells_count: number
}

export type CodeSmell = {
    filepath: string
    smell_type: string
    severity: 'low' | 'medium' | 'high' | 'critical'
    line_start?: number
    line_end?: number
    message: string
}

export type AnalyzeResponse = {
    repo_id: number
    files_analyzed: number
    total_smells: number
    metrics: FileMetrics[]
}

export type AnalysisSummary = {
    file_count: number
    avg_cyclomatic_complexity: number
    max_cyclomatic_complexity: number
    avg_wmc: number
    avg_cbo: number
    avg_lcom: number
    total_code_smells: number
    total_loc: number
}

// API Functions

/**
 * Lance l'analyse statique d'un repository
 */
export async function analyzeRepository(repoId: number, commitSha?: string): Promise<AnalyzeResponse> {
    const { data } = await analyseStatiqueClient.post<AnalyzeResponse>('/analyze', {
        repo_id: repoId,
        commit_sha: commitSha
    })
    return data
}

/**
 * Récupère les métriques d'un repository
 */
export async function getRepositoryMetrics(repoId: number): Promise<{
    repo_id: number
    files: number
    metrics: FileMetrics[]
}> {
    const { data } = await analyseStatiqueClient.get(`/metrics/${repoId}`)
    return data
}

/**
 * Récupère les code smells d'un repository
 */
export async function getCodeSmells(repoId: number): Promise<{
    repo_id: number
    total_smells: number
    smells: CodeSmell[]
}> {
    const { data } = await analyseStatiqueClient.get(`/smells/${repoId}`)
    return data
}

/**
 * Récupère le résumé de l'analyse d'un repository
 */
export async function getAnalysisSummary(repoId: number): Promise<{
    repo_id: number
    summary: AnalysisSummary
}> {
    const { data } = await analyseStatiqueClient.get(`/summary/${repoId}`)
    return data
}

/**
 * Vérifie la santé du service d'analyse statique
 */
export async function checkHealth(): Promise<{
    status: string
    database: string
}> {
    const { data } = await analyseStatiqueClient.get('/health')
    return data
}
