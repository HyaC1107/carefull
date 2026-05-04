import { initializeApp, getApps } from 'firebase/app'
import { getMessaging, getToken, isSupported } from 'firebase/messaging'
import { getStoredToken, requestJson } from './api'

let fcmRegistrationPromise = null
let lastRegisteredRegistrationKey = ''
const FIREBASE_CONFIG = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
}

function buildFirebaseMessagingSwUrl() {
  const params = new URLSearchParams(
    Object.entries(FIREBASE_CONFIG).filter(([, value]) => String(value || '').trim()),
  )

  return `/firebase-messaging-sw.js?${params.toString()}`
}

function hasFirebaseConfig() {
  return Object.values(FIREBASE_CONFIG).every((value) => String(value || '').trim())
}

function buildRegistrationKey(authToken) {
  return [
    authToken,
    window.location.origin,
    FIREBASE_CONFIG.projectId,
    FIREBASE_CONFIG.messagingSenderId,
    FIREBASE_CONFIG.appId,
    import.meta.env.VITE_FIREBASE_VAPID_KEY,
  ].join('|')
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

  try {
    const permission = await Notification.requestPermission()

    if (permission === 'default') {
      console.warn('[FCM] Notification permission remains default. User gesture may be required.')
    }

    return permission
  } catch (error) {
    console.warn('[FCM] Notification permission request failed:', error)
    return Notification.permission
  }
}

export async function registerFcmTokenForCurrentUser() {
  const authToken = getStoredToken()

  if (!authToken) {
    console.warn('[FCM] skipped: auth token is missing.')
    return
  }

  const registrationKey = buildRegistrationKey(authToken)

  if (lastRegisteredRegistrationKey === registrationKey) {
    return
  }

  if (fcmRegistrationPromise) {
    return fcmRegistrationPromise
  }

  fcmRegistrationPromise = registerFcmToken(registrationKey)
    .finally(() => {
      fcmRegistrationPromise = null
    })

  return fcmRegistrationPromise
}

async function registerFcmToken(registrationKey) {
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
      buildFirebaseMessagingSwUrl(),
      { scope: '/' },
    )
    const readyRegistration = await navigator.serviceWorker.ready
    const messaging = getMessaging(getFirebaseApp())
    const fcmToken = await getToken(messaging, {
      vapidKey: import.meta.env.VITE_FIREBASE_VAPID_KEY,
      serviceWorkerRegistration: readyRegistration || registration,
    })

    if (!fcmToken) {
      console.warn('[FCM] FCM token was not issued.')
      return
    }

    console.info('[FCM] token issued:', fcmToken.slice(0, 12))

    await requestJson('/api/push/register', {
      method: 'POST',
      auth: true,
      body: {
        fcm_token: fcmToken,
        device_type: 'web',
      },
    })

    lastRegisteredRegistrationKey = registrationKey
  } catch (error) {
    console.warn('[FCM] Failed to register FCM token:', error)
  }
}
