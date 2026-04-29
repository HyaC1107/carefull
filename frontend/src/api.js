const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() || ''

export const API_BASE_URL = configuredApiBaseUrl.replace(/\/+$/, '')

if (!API_BASE_URL) {
  console.error('VITE_API_BASE_URL is not configured. Set it in frontend/.env.')
}

export const TOKEN_STORAGE_KEY = 'carefull_token'

export function getStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY) || ''
}

export function hasStoredToken() {
  return Boolean(getStoredToken())
}

export function getStoredAuthPayload() {
  const token = getStoredToken()
  if (!token) return null

  const [, encodedPayload] = token.split('.')
  if (!encodedPayload) return null

  try {
    const normalized = encodedPayload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(
      normalized.length + ((4 - (normalized.length % 4)) % 4),
      '=',
    )
    const binary = atob(padded)
    const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0))
    return JSON.parse(new TextDecoder('utf-8').decode(bytes))
  } catch {
    return null
  }
}

export async function requestJson(
  path,
  { method = 'GET', auth = false, body, headers = {} } = {},
) {
  const token = getStoredToken()

  if (!API_BASE_URL) throw new Error('VITE_API_BASE_URL is not configured.')
  if (auth && !token) throw new Error('Authentication token is missing.')

  const requestHeaders = {
    Accept: 'application/json',
    ...headers,
  }

  if (body !== undefined) requestHeaders['Content-Type'] = 'application/json'
  if (auth) requestHeaders.Authorization = `Bearer ${token}`

  const response = await fetch(new URL(path, API_BASE_URL), {
    method,
    headers: requestHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  const data = await response.json().catch(() => null)

  if (!response.ok || data?.success === false) {
    const error = new Error(data?.message || 'Request failed.')
    error.status = response.status
    error.data = data
    throw error
  }

  return data || {}
}
