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

  if (!token) {
    return null
  }

  const [, encodedPayload] = token.split('.')

  if (!encodedPayload) {
    return null
  }

  try {
    const normalizedPayload = encodedPayload
      .replace(/-/g, '+')
      .replace(/_/g, '/')
    const paddedPayload = normalizedPayload.padEnd(
      normalizedPayload.length +
        ((4 - (normalizedPayload.length % 4)) % 4),
      '=',
    )
    const binaryPayload = atob(paddedPayload)
    const payloadBytes = Uint8Array.from(binaryPayload, (char) =>
      char.charCodeAt(0),
    )
    const decodedPayload = new TextDecoder('utf-8').decode(payloadBytes)

    return JSON.parse(decodedPayload)
  } catch (error) {
    console.error('failed to decode auth payload:', error)
    return null
  }
}

export async function requestJson(
  path,
  { method = 'GET', auth = false, body, headers = {} } = {},
) {
  const token = getStoredToken()

  if (!API_BASE_URL) {
    throw new Error('VITE_API_BASE_URL is not configured.')
  }

  if (auth && !token) {
    throw new Error('Authentication token is missing.')
  }

  const requestHeaders = {
    Accept: 'application/json',
    ...headers,
  }

  if (body !== undefined) {
    requestHeaders['Content-Type'] = 'application/json'
  }

  if (auth) {
    requestHeaders.Authorization = `Bearer ${token}`
  }

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
