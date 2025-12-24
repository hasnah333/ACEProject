import axios, { AxiosError } from 'axios'
import type { AxiosRequestConfig } from 'axios'
import API_CONFIG from '../../config/api'

export type ApiError = {
  status?: number
  message: string
  details?: unknown
}

export type RequestState<T> = {
  loading: boolean
  data?: T
  error?: ApiError
}

let authToken: string | null = null

export function setAuthToken(token: string | null) {
  authToken = token
}

// Client pour le backend (collecte-depots)
export const backendClient = axios.create({
  baseURL: API_CONFIG.BACKEND_URL,
  timeout: 120_000, // 2 minutes pour la collecte
})

// Client pour le service ML (timeout plus long pour l'entraînement)
export const mlServiceClient = axios.create({
  baseURL: API_CONFIG.ML_SERVICE_URL,
  timeout: 600_000, // 10 minutes pour l'entraînement
})

// Client pour le prétraitement (timeout plus long pour la génération de features)
export const pretraitementClient = axios.create({
  baseURL: API_CONFIG.PRETRAITEMENT_URL,
  timeout: 300_000, // 5 minutes pour la génération de features
})

// Client pour le moteur de priorisation
export const priorisationClient = axios.create({
  baseURL: API_CONFIG.MOTEUR_PRIORISATION_URL,
  timeout: 30_000,
})

// Client par défaut (pour compatibilité)
export const apiClient = backendClient

// Intercepteur pour l'authentification
const addAuthToken = (config: any) => {
  const token = authToken ?? window.localStorage.getItem('kc_token')
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}

backendClient.interceptors.request.use(addAuthToken)
mlServiceClient.interceptors.request.use(addAuthToken)
pretraitementClient.interceptors.request.use(addAuthToken)
priorisationClient.interceptors.request.use(addAuthToken)

// Intercepteur pour les erreurs
const handleError = (error: AxiosError) => {
  const apiError: ApiError = {
    status: error.response?.status,
    message:
      (error.response?.data as any)?.message ??
      error.message ??
      'Unexpected API error',
    details: error.response?.data,
  }
  console.error('API error', apiError)
  return Promise.reject(apiError)
}

backendClient.interceptors.response.use((response: any) => response, handleError)
mlServiceClient.interceptors.response.use((response: any) => response, handleError)
pretraitementClient.interceptors.response.use((response: any) => response, handleError)
priorisationClient.interceptors.response.use((response: any) => response, handleError)

/**
 * Helper to drive a simple loading/data/error state machine outside React.
 * Callers typically wrap this in a hook, e.g. useState-based.
 */
export async function runWithState<T>(
  config: AxiosRequestConfig,
  setState: (state: RequestState<T>) => void,
): Promise<T> {
  setState({ loading: true })
  try {
    const { data } = await apiClient.request<T>(config)
    setState({ loading: false, data })
    return data
  } catch (error) {
    const apiError = error as ApiError
    setState({ loading: false, error: apiError })
    throw apiError
  }
}



