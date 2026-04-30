// 백그라운드 푸시 수신 서비스 워커
// Firebase SDK 없이 Web Push 표준 API만 사용 — SDK init 실패로 SW 전체가 죽는 문제 방지

self.addEventListener('push', (event) => {
  const payload = event.data ? event.data.json() : {}
  const notification = payload.notification || {}
  const data = payload.data || {}
  const title = notification.title || data.title || 'CARE-FULL 알림'
  const body  = notification.body  || data.body  || ''

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon:  '/favicons/favicon.ico',
      badge: '/favicons/favicon.ico',
      data,
    })
  )
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
