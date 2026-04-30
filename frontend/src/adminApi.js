import { API_BASE_URL } from './api'

const ADMIN_TOKEN_KEY = 'carefull_admin_token'

export function getAdminToken() {
  return localStorage.getItem(ADMIN_TOKEN_KEY) || ''
}

export function hasAdminToken() {
  return Boolean(getAdminToken())
}

export function setAdminToken(token) {
  localStorage.setItem(ADMIN_TOKEN_KEY, token)
}

export function clearAdminToken() {
  localStorage.removeItem(ADMIN_TOKEN_KEY)
}

export async function adminRequest(path, { method = 'GET', body } = {}) {
  const token = getAdminToken()
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(new URL(path, API_BASE_URL), {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  const data = await res.json().catch(() => null)

  if (!res.ok || data?.success === false) {
    const err = new Error(data?.message || '요청 실패')
    err.status = res.status
    throw err
  }

  return data || {}
}

export async function sendTestPush(mem_id, title, body) {
  return adminRequest('/api/admin/test/push', {
    method: 'POST',
    body: { mem_id, title, body }
  })
}
