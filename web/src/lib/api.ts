import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { TokenResponse } from '../types/api'
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setRefreshToken,
} from './tokens'

export const api = axios.create({
  baseURL: '/api/v1',
})

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const access = getAccessToken()
  if (access) config.headers.Authorization = `Bearer ${access}`
  return config
})

let refreshPromise: Promise<string | null> | null = null

function redirectToLogin(): void {
  if (window.location.pathname !== '/login') {
    window.location.assign('/login')
  }
}

async function tryRefresh(): Promise<string | null> {
  const refresh = getRefreshToken()
  if (!refresh) return null
  try {
    const { data } = await axios.post<TokenResponse>(
      '/api/v1/auth/refresh',
      { refresh_token: refresh },
    )
    setAccessToken(data.access_token)
    setRefreshToken(data.refresh_token)
    return data.access_token
  } catch {
    clearTokens()
    return null
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as
      | (InternalAxiosRequestConfig & { _retried?: boolean })
      | undefined
    if (error.response?.status === 401 && original && !original._retried) {
      original._retried = true
      refreshPromise ??= tryRefresh().finally(() => {
        refreshPromise = null
      })
      const access = await refreshPromise
      if (access) {
        original.headers.Authorization = `Bearer ${access}`
        return api(original)
      }
      clearTokens()
      redirectToLogin()
    }
    throw error
  },
)

export interface ApiErrorDetail {
  detail?: string | { msg: string }[]
}

export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = (err.response?.data as ApiErrorDetail | undefined)?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join('; ')
  }
  if (err instanceof Error) return err.message
  return 'Unexpected error'
}