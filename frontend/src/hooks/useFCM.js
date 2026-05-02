import { useEffect } from 'react'
import { getMessaging, isSupported, onMessage } from 'firebase/messaging'
import { firebaseApp } from '../firebase'
import { hasStoredToken } from '../api'

const VAPID_KEY = import.meta.env.VITE_FIREBASE_VAPID_KEY

export function useFCM() {
  useEffect(() => {
    if (!hasStoredToken()) return

    let unsubscribe = null
    let cancelled = false

    async function bindForegroundListener() {
      if (!('Notification' in window)) {
        console.warn('[FCM] Notification API is not supported.')
        return
      }

      if (!('serviceWorker' in navigator)) {
        console.warn('[FCM] Service Worker is not supported.')
        return
      }

      if (!VAPID_KEY) {
        console.warn('[FCM] Firebase VAPID key is missing.')
        return
      }

      const supported = await isSupported().catch(() => false)

      if (!supported) {
        console.warn('[FCM] Firebase Messaging is not supported in this browser.')
        return
      }

      if (cancelled) return

      try {
        const messaging = getMessaging(firebaseApp)

        unsubscribe = onMessage(messaging, (payload) => {
          const title = payload?.notification?.title || payload?.data?.title || 'Carefull'
          const body = payload?.notification?.body || payload?.data?.body || ''
          const data = payload?.data || {}

          console.info('[FCM] foreground message received:', {
            title,
            body,
            data,
          })

          if (Notification.permission === 'granted') {
            navigator.serviceWorker.ready
              .then((registration) => registration.showNotification(title, {
                body,
                icon: '/favicons/favicon.ico',
                badge: '/favicons/favicon.ico',
                data,
              }))
              .catch((error) => {
                console.warn('[FCM] Failed to show foreground notification:', error)
              })
          } else {
            console.warn('[FCM] Notification permission is not granted.')
          }

          window.dispatchEvent(
            new CustomEvent('carefull:push-notification', { detail: payload })
          )
        })
      } catch (e) {
        console.warn('[FCM] onMessage setup failed:', e.message)
      }
    }

    bindForegroundListener()

    return () => {
      cancelled = true
      unsubscribe?.()
    }
  }, [])
}
