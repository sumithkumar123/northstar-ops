// Minimal auth state — stored in localStorage, no extra library needed

export interface AuthUser {
  sub: string
  role: string
  store_id: string | null
  region_id: string | null
}

function decodeJWT(token: string): AuthUser | null {
  try {
    const payload = token.split('.')[1]
    const decoded = JSON.parse(atob(payload.replace(/-/g, '+').replace(/_/g, '/')))
    return { sub: decoded.sub, role: decoded.role, store_id: decoded.store_id, region_id: decoded.region_id }
  } catch {
    return null
  }
}

export const authStore = {
  getToken: (): string | null => localStorage.getItem('access_token'),
  getRefreshToken: (): string | null => localStorage.getItem('refresh_token'),
  getUser: (): AuthUser | null => {
    const token = localStorage.getItem('access_token')
    return token ? decodeJWT(token) : null
  },
  login(access_token: string, refresh_token: string) {
    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh_token)
  },
  logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  },
  isLoggedIn: (): boolean => !!localStorage.getItem('access_token'),
}
