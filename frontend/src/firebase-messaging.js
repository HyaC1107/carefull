import { initializeApp, getApps } from 'firebase/app'
import { getMessaging, getToken, isSupported } from 'firebase/messaging'
import { getStoredToken, requestJson } from './api'

const FCM_SESSION_KEY = 'carefull_fcm_registered'
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
  console.log('[FCM] registerFcmTokenForCurrentUser called')
  console.log('[FCM] register init')
  console.log('[FCM] session flag:', sessionStorage.getItem(FCM_SESSION_KEY))

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

  fcmRegistrationPromise = registerFcmToken(authToken, registrationKey)
    .catch((error) => {
      console.warn('[FCM] Failed to register FCM token:', error)
    })
    .finally(() => {
      fcmRegistrationPromise = null
    })

  return fcmRegistrationPromise
}

async function registerFcmToken(authToken, registrationKey) {

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

  if ('Notification' in window) {
    console.log('[FCM] permission before request:', Notification.permission)
  }

  const permission = await resolveNotificationPermission()
  console.log('[FCM] permission after request:', permission)

  if (permission !== 'granted') {
    console.warn('[FCM] skipped: notification permission is not granted.', permission)
    return
  }

  try {
    const serviceWorkerUrl = buildFirebaseMessagingSwUrl()
    console.info('[FCM] service worker registering:', {
      path: '/firebase-messaging-sw.js',
      scope: '/'
    })
    const registration = await navigator.serviceWorker.register(
      serviceWorkerUrl,
      { scope: '/' },
    )
    console.info('[FCM] service worker registered:', {
      scope: registration.scope,
      active: Boolean(registration.active),
      waiting: Boolean(registration.waiting),
      installing: Boolean(registration.installing),
    })

    registration.addEventListener('updatefound', () => {
      console.info('[FCM] service worker update found.')
    })

    registration.update()
      .then(() => {
        console.info('[FCM] service worker update checked.')
      })
      .catch((error) => {
        console.warn('[FCM] service worker update check failed:', error)
      })

    const readyRegistration = await navigator.serviceWorker.ready
    console.log('[FCM] service worker ready:', readyRegistration.scope)
    const messaging = getMessaging(getFirebaseApp())
    let fcmToken = ''

    try {
      console.log('[FCM] calling getToken')
      fcmToken = await getToken(messaging, {
        vapidKey: import.meta.env.VITE_FIREBASE_VAPID_KEY,
        serviceWorkerRegistration: readyRegistration || registration,
      })
    } catch (error) {
      console.error('[FCM] getToken failed:', error)
      throw error
    }

    if (!fcmToken) {
      console.warn('[FCM] FCM token was not issued.')
      return
    }

    console.log('[FCM] token received:', fcmToken?.slice(0, 12))
    console.log('[FCM] getToken success', fcmToken.slice(0, 12))

    console.log('[FCM] registering token')
    try {
      console.log('[FCM] calling /api/push/register')
      await requestJson('/api/push/register', {
        method: 'POST',
        auth: true,
        body: {
          fcm_token: fcmToken,
          device_type: 'web',
        },
      })
      console.log('[FCM] push/register success')
    } catch (error) {
      console.error('[FCM] push/register failed:', error)
      throw error
    }

    sessionStorage.setItem(FCM_SESSION_KEY, 'true')
    lastRegisteredRegistrationKey = registrationKey
    console.log('[FCM] token registered')
  } catch (error) {
    console.warn('[FCM] Failed to register FCM token:', error)
  }
}
