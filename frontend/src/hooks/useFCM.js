import { useEffect } from 'react'
import { getMessaging, getToken, onMessage } from 'firebase/messaging'
import { firebaseApp } from '../firebase'
import { hasStoredToken, requestJson } from '../api'

const VAPID_KEY = import.meta.env.VITE_FIREBASE_VAPID_KEY
const FCM_SW_PATH = '/firebase-messaging-sw.js'

export function useFCM() {
  useEffect(() => {
    if (!hasStoredToken()) return
    if (!('Notification' in window) || !('serviceWorker' in navigator)) return
    if (!VAPID_KEY) return

    const register = async () => {
      try {
        const permission = await Notification.requestPermission()
        if (permission !== 'granted') return

        // Vite PWA sw가 아닌 Firebase 전용 sw를 명시적으로 등록해서 사용
        const sw_reg = await navigator.serviceWorker.register(FCM_SW_PATH)

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

        // 포그라운드(탭이 열려있을 때) 알림 처리
        // FCM이 onMessage로 전달하면 서비스 워커를 거치지 않으므로 직접 띄워야 함
        onMessage(messaging, async (payload) => {
          const title = payload.notification?.title || 'CARE-FULL 알림'
          const body  = payload.notification?.body  || ''

          // ServiceWorker를 통해 알림 표시 (new Notification()보다 안정적)
          const reg = await navigator.serviceWorker.getRegistration(FCM_SW_PATH)
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
        console.warn('[FCM] registration failed:', e.message)
      }
    }

    register()
  }, [])
}
