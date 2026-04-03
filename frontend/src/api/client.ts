// Thin fetch wrapper: injects Bearer token, handles 401 token refresh

import { authStore } from '../store/auth'

const BASE = ''  // relative URLs — nginx or vite proxy handles routing

async function request<T>(method: string, path: string, body?: unknown, retry = true): Promise<T> {
  const token = authStore.getToken()
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  })

  // Auto-refresh on 401
  if (res.status === 401 && retry) {
    const refreshToken = authStore.getRefreshToken()
    if (refreshToken) {
      const refreshRes = await fetch('/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (refreshRes.ok) {
        const data = await refreshRes.json()
        authStore.login(data.access_token, data.refresh_token)
        return request<T>(method, path, body, false)  // retry once
      }
    }
    authStore.logout()
    window.location.href = '/login'
    throw new Error('Session expired')
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }

  return res.json() as Promise<T>
}

export const api = {
  get:   <T>(path: string)               => request<T>('GET', path),
  post:  <T>(path: string, body: unknown) => request<T>('POST', path, body),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, body),
}
