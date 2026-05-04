import { useEffect, useState } from 'react'
import { hasStoredToken, requestJson } from '../api'

export function useUnreadCount() {
  const [unreadCount, setUnreadCount] = useState(0)

  useEffect(() => {
    if (!hasStoredToken()) return
    requestJson('/api/notification/unread-count', { auth: true })
      .then((data) => setUnreadCount(data?.count ?? 0))
      .catch(() => {})
  }, [])

  useEffect(() => {
    const handler = () => setUnreadCount((prev) => prev + 1)
    window.addEventListener('carefull:push-notification', handler)
    return () => window.removeEventListener('carefull:push-notification', handler)
  }, [])

  return unreadCount
}
