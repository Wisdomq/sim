const ACCESS_KEY = 'simcards.access_token'
const REFRESH_KEY = 'simcards.refresh_token'

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_KEY)
}

export function setAccessToken(token: string | null): void {
  if (token === null) localStorage.removeItem(ACCESS_KEY)
  else localStorage.setItem(ACCESS_KEY, token)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY)
}

export function setRefreshToken(token: string | null): void {
  if (token === null) localStorage.removeItem(REFRESH_KEY)
  else localStorage.setItem(REFRESH_KEY, token)
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
}