self.addEventListener('push', (event) => {
  let payload = {}

  try {
    payload = event.data ? event.data.json() : {}
  } catch (error) {
    console.warn('[FCM SW] push payload parse failed:', error)
  }

  const notification = payload.notification || {}
  const data = payload.data || {}
  const title = notification.title || data.title || 'Carefull'
  const options = {
    body: notification.body || data.body || '',
    icon: '/favicons/favicon.ico',
    badge: '/favicons/favicon.ico',
    data,
  }

  console.info('[FCM SW] push event received:', {
    title,
    data,
  })

  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('install', () => {
  console.info('[FCM SW] installed.')
})

self.addEventListener('activate', () => {
  console.info('[FCM SW] activated.')
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  const targetUrl = event.notification.data?.url || self.registration.scope

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clients) => {
        const matchedClient = clients.find((client) => client.url === targetUrl)

        if (matchedClient) {
          return matchedClient.focus()
        }

        return self.clients.openWindow(targetUrl)
      }),
  )
})

importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js')
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js')

const firebaseConfig = Object.fromEntries(new URL(self.location.href).searchParams.entries())

if (Object.values(firebaseConfig).every((value) => String(value || '').trim())) {
  firebase.initializeApp(firebaseConfig)
  console.info('[FCM SW] Firebase initialized.')
} else {
  console.warn('[FCM SW] Firebase config is missing.')
}

const messaging = firebase.apps.length > 0 ? firebase.messaging() : null

if (messaging) {
  messaging.onBackgroundMessage((payload) => {
    console.info('[FCM SW] background message received:', {
      title: payload?.notification?.title,
      body: payload?.notification?.body,
      data: payload?.data,
    })

    const title = payload?.notification?.title || payload?.data?.title || 'Carefull'
    const body = payload?.notification?.body || payload?.data?.body || ''

    self.registration.showNotification(title, {
      body,
      icon: '/favicons/favicon.ico',
      badge: '/favicons/favicon.ico',
      data: payload?.data || {},
    })
  })
}
