import { initializeApp, getApps } from 'firebase/app'
import { getMessaging, getToken, isSupported } from 'firebase/messaging'
import { hasStoredToken, requestJson } from './api'

const FCM_SESSION_KEY = 'carefull_fcm_registered'
const FIREBASE_CONFIG = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

function hasFirebaseConfig() {
  return Object.values(FIREBASE_CONFIG).every((value) => String(value || '').trim())
}

function getFirebaseApp() {
  return getApps().length > 0 ? getApps()[0] : initializeApp(FIREBASE_CONFIG)
}

async function resolveNotificationPermission() {
  if (!('Notification' in window)) {
    console.warn('[FCM] Notification API is not supported.')
    return ''
  }

  if (Notification.permission === 'granted') {
    return 'granted'
  }

  if (Notification.permission === 'denied') {
    console.warn('[FCM] Notification permission is denied.')
    return 'denied'
  }

  return Notification.requestPermission()
}

export async function registerFcmTokenForCurrentUser() {
  if (!hasStoredToken() || sessionStorage.getItem(FCM_SESSION_KEY) === 'true') {
    return
  }

  if (!window.isSecureContext) {
    console.warn('[FCM] A secure browser context is required for push messaging.')
    return
  }

  if (!('serviceWorker' in navigator)) {
    console.warn('[FCM] Service Worker is not supported.')
    return
  }

  if (!hasFirebaseConfig() || !import.meta.env.VITE_FIREBASE_VAPID_KEY) {
    console.warn('[FCM] Firebase web configuration is missing.')
    return
  }

  const supported = await isSupported().catch(() => false)

  if (!supported) {
    console.warn('[FCM] Firebase Messaging is not supported in this browser.')
    return
  }

  const permission = await resolveNotificationPermission()

  if (permission !== 'granted') {
    return
  }

  try {
    const registration = await navigator.serviceWorker.register(
      '/firebase-messaging-sw.js',
    )
    const messaging = getMessaging(getFirebaseApp())
    const fcmToken = await getToken(messaging, {
      vapidKey: import.meta.env.VITE_FIREBASE_VAPID_KEY,
      serviceWorkerRegistration: registration,
    })

    if (!fcmToken) {
      console.warn('[FCM] FCM token was not issued.')
      return
    }

    console.log('[FCM TOKEN]', fcmToken)

    await requestJson('/api/push/register', {
      method: 'POST',
      auth: true,
      body: {
        fcm_token: fcmToken,
        device_type: 'web',
      },
    })

    sessionStorage.setItem(FCM_SESSION_KEY, 'true')
  } catch (error) {
    console.warn('[FCM] Failed to register FCM token:', error)
  }
}
