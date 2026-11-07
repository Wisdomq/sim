import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api } from './api'
import type { CurrentUser, TokenResponse } from '../types/api'
import {
  clearTokens,
  getAccessToken,
  setAccessToken,
  setRefreshToken,
} from './tokens'

interface AuthState {
  status: 'loading' | 'authed' | 'anonymous'
  user: CurrentUser | null
  login: (email: string, password: string) => Promise<CurrentUser>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthState['status']>('loading')
  const [user, setUser] = useState<CurrentUser | null>(null)

  useEffect(() => {
    let cancelled = false
    async function restore() {
      if (!getAccessToken()) {
        setStatus('anonymous')
        return
      }
      try {
        const { data } = await api.get<CurrentUser>('/auth/me')
        if (!cancelled) {
          setUser(data)
          setStatus('authed')
        }
      } catch {
        if (!cancelled) {
          setUser(null)
          setStatus('anonymous')
        }
      }
    }
    void restore()
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await api.post<TokenResponse>('/auth/login', {
      email,
      password,
      device_info: { client: 'simcards-web' },
    })
    setAccessToken(data.access_token)
    setRefreshToken(data.refresh_token)
    const me = await api.get<CurrentUser>('/auth/me')
    setUser(me.data)
    setStatus('authed')
    return me.data
  }, [])

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
    setStatus('anonymous')
  }, [])

  const value = useMemo(
    () => ({ status, user, login, logout }),
    [status, user, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}