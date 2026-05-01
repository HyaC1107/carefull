import { useEffect } from 'react'
import { getMessaging, onMessage } from 'firebase/messaging'
import { firebaseApp } from '../firebase'
import { hasStoredToken } from '../api'

export function useFCM() {
  useEffect(() => {
    if (!hasStoredToken()) return
    if (!('Notification' in window) || !('serviceWorker' in navigator)) return

    const setup = async () => {
      try {
        const messaging = getMessaging(firebaseApp)

        // 포그라운드(탭이 열려있을 때) 알림 처리
        onMessage(messaging, async (payload) => {
          const title = payload.notification?.title || 'CARE-FULL 알림'
          const body = payload.notification?.body || ''

          const reg = await navigator.serviceWorker.ready
          if (reg) {
            reg.showNotification(title, {
              body,
              icon: '/favicons/favicon.ico',
              badge: '/favicons/favicon.ico',
            })
          }

          window.dispatchEvent(
            new CustomEvent('carefull:push-notification', { detail: payload })
          )
        })
      } catch (e) {
        console.warn('[FCM] onMessage setup failed:', e.message)
      }
    }

    setup()
  }, [])
}
