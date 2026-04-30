import { useEffect } from 'react'
import { getMessaging, isSupported, onMessage } from 'firebase/messaging'
import { firebaseApp } from '../firebase'

const VAPID_KEY = import.meta.env.VITE_FIREBASE_VAPID_KEY

export function useFCM() {
  useEffect(() => {
    let unsubscribe = null
    let cancelled = false

    async function bindForegroundListener() {
      if (!('Notification' in window)) {
        console.warn('[FCM] foreground listener skipped: Notification API is not supported.')
        return
      }

      if (!('serviceWorker' in navigator)) {
        console.warn('[FCM] foreground listener skipped: Service Worker is not supported.')
        return
      }

      if (!VAPID_KEY) {
        console.warn('[FCM] foreground listener skipped: VAPID key is missing.')
        return
      }

      const supported = await isSupported().catch(() => false)

      if (!supported) {
        console.warn('[FCM] foreground listener skipped: Firebase Messaging is not supported.')
        return
      }

      if (cancelled) {
        return
      }

      try {
        const messaging = getMessaging(firebaseApp)

        unsubscribe = onMessage(messaging, (payload) => {
          console.info('[FCM] foreground message received:', {
            title: payload?.notification?.title,
            body: payload?.notification?.body,
            data: payload?.data,
          })

          if (Notification.permission === 'granted') {
            const title = payload?.notification?.title || payload?.data?.title || 'Carefull'
            const body = payload?.notification?.body || payload?.data?.body || ''

            navigator.serviceWorker.ready
              .then((registration) =>
                registration.showNotification(title, {
                  body,
                  icon: '/favicons/favicon.ico',
                  badge: '/favicons/favicon.ico',
                  data: payload?.data || {},
                }),
              )
              .catch((error) => {
                console.warn('[FCM] foreground notification failed:', error)
              })
          } else {
            console.warn('[FCM] foreground notification skipped:', Notification.permission)
          }

          window.dispatchEvent(
            new CustomEvent('carefull:push-notification', { detail: payload })
          )
        })
      } catch (e) {
        console.warn('[FCM] foreground listener failed:', e.message)
      }
    }

    bindForegroundListener()

    return () => {
      cancelled = true
      unsubscribe?.()
    }
  }, [])
}
