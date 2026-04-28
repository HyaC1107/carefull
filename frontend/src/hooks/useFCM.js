import { useEffect } from 'react'
import { getMessaging, getToken, onMessage } from 'firebase/messaging'
import { firebaseApp } from '../firebase'
import { hasStoredToken, requestJson } from '../api'

const VAPID_KEY = import.meta.env.VITE_FIREBASE_VAPID_KEY

export function useFCM() {
  useEffect(() => {
    if (!hasStoredToken()) return
    if (!('Notification' in window) || !('serviceWorker' in navigator)) return
    if (!VAPID_KEY) return

    const register = async () => {
      try {
        const permission = await Notification.requestPermission()
        if (permission !== 'granted') return

        const sw_reg = await navigator.serviceWorker.register(
          '/firebase-messaging-sw.js',
          { scope: '/' }
        )

        const messaging = getMessaging(firebaseApp)
        const token = await getToken(messaging, {
          vapidKey: VAPID_KEY,
          serviceWorkerRegistration: sw_reg,
        })

        if (token) {
          await requestJson('/api/notification/fcm-token', {
            method: 'POST',
            auth: true,
            body: { fcm_token: token },
          })
        }

        onMessage(messaging, (payload) => {
          window.dispatchEvent(
            new CustomEvent('carefull:push-notification', { detail: payload })
          )
        })
      } catch (e) {
        console.warn('[FCM] registration failed:', e.message)
      }
    }

    register()
  }, [])
}
