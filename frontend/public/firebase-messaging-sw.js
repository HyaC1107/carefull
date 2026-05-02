// 백그라운드 푸시 수신 서비스 워커
// Firebase SDK 없이 Web Push 표준 API만 사용 — SDK init 실패로 SW 전체가 죽는 문제 방지

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
  const body = notification.body || data.body || ''

  console.info('[FCM SW] push event received:', {
    title,
    data,
  })

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: '/favicons/favicon.ico',
      badge: '/favicons/favicon.ico',
      data,
    })
  )
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
        const matched = clients.find((c) => c.url === targetUrl)
        return matched ? matched.focus() : self.clients.openWindow(targetUrl)
      })
  )
})
