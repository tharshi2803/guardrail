// Thin client over the ragqaapp backend. HTTP Basic auth: the credentials are
// held in memory + sessionStorage and sent on every request. Requests go to
// `/api/*`, proxied to the FastAPI backend in dev (see vite.config.ts).
import type { RulesFile } from '@/types/guardrails'

const API_BASE = '/api'
const STORAGE_KEY = 'guardrail-auth'

let authHeader: string | null = sessionStorage.getItem(STORAGE_KEY)

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export function isAuthenticated(): boolean {
  return authHeader !== null
}

export function logout(): void {
  authHeader = null
  sessionStorage.removeItem(STORAGE_KEY)
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const h: Record<string, string> = { ...extra }
  if (authHeader) h['Authorization'] = authHeader
  return h
}

/** Validate credentials against GET /auth; store them on success. */
export async function login(username: string, password: string): Promise<void> {
  const header = 'Basic ' + btoa(`${username}:${password}`)
  let res: Response
  try {
    res = await fetch(`${API_BASE}/auth`, { headers: { Authorization: header } })
  } catch {
    throw new ApiError(0, 'Could not reach the server. Is the backend running?')
  }
  if (res.status === 401) throw new ApiError(401, 'Invalid username or password.')
  if (!res.ok) throw new ApiError(res.status, `Login failed (${res.status}).`)
  authHeader = header
  sessionStorage.setItem(STORAGE_KEY, header)
}

export async function getRules(): Promise<RulesFile> {
  const res = await fetch(`${API_BASE}/rules`, { headers: authHeaders() })
  if (res.status === 401) {
    logout()
    throw new ApiError(401, 'Session expired. Please sign in again.')
  }
  if (!res.ok) throw new ApiError(res.status, `Failed to load rules (${res.status}).`)
  return res.json()
}

/** Tell the backend to re-read guardrails.yaml from disk (picks up out-of-band edits). */
export async function reloadRules(): Promise<void> {
  const res = await fetch(`${API_BASE}/rules/reload`, { method: 'POST', headers: authHeaders() })
  if (res.status === 401) {
    logout()
    throw new ApiError(401, 'Session expired. Please sign in again.')
  }
  if (!res.ok) throw new ApiError(res.status, `Reload failed (${res.status}).`)
}

export async function putRules(rules: RulesFile): Promise<RulesFile> {
  const res = await fetch(`${API_BASE}/rules`, {
    method: 'PUT',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(rules),
  })
  if (res.status === 401) {
    logout()
    throw new ApiError(401, 'Session expired. Please sign in again.')
  }
  if (!res.ok) {
    // The backend returns 422 with { detail } on a validation failure.
    let detail = `Save failed (${res.status}).`
    try {
      const body = await res.json()
      if (body?.detail) {
        detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      }
    } catch {
      /* non-JSON error body — keep the generic message */
    }
    throw new ApiError(res.status, detail)
  }
  return res.json()
}
