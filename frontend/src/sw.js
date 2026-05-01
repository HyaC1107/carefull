import { cleanupOutdatedCaches, precacheAndRoute } from 'workbox-precaching'
import { NavigationRoute, registerRoute } from 'workbox-routing'
import { NetworkFirst, StaleWhileRevalidate } from 'workbox-strategies'
import { ExpirationPlugin } from 'workbox-expiration'

// Workbox precache (VitePWA가 빌드 시 __WB_MANIFEST를 주입)
cleanupOutdatedCaches()
precacheAndRoute(self.__WB_MANIFEST)

// SPA 네비게이션 폴백
registerRoute(
  new NavigationRoute(
    new NetworkFirst({
      cacheName: 'pages-cache',
      plugins: [new ExpirationPlugin({ maxEntries: 10, maxAgeSeconds: 86400 })],
    })
  )
)

// 스타일/스크립트/워커 캐싱
registerRoute(
  ({ request }) => ['style', 'script', 'worker'].includes(request.destination),
  new StaleWhileRevalidate({ cacheName: 'assets-cache' })
)

// 이미지 캐싱
registerRoute(
  ({ request }) => request.destination === 'image',
  new StaleWhileRevalidate({
    cacheName: 'image-cache',
    plugins: [new ExpirationPlugin({ maxEntries: 50, maxAgeSeconds: 2592000 })],
  })
)

// FCM 백그라운드 push 수신 (Firebase SDK 없이 Web Push 표준으로 처리)
self.addEventListener('push', (event) => {
  const payload = event.data ? event.data.json() : {}
  const notification = payload.notification || {}
  const data = payload.data || {}
  const title = notification.title || data.title || 'CARE-FULL 알림'
  const body = notification.body || data.body || ''

  event.waitUntil(
    self.registration.showNotification(title, {
      body,
      icon: '/favicons/favicon.ico',
      badge: '/favicons/favicon.ico',
      data,
    })
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  const targetUrl = event.notification.data?.url || self.registration.scope

  event.waitUntil(
    self.clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((clients) => {
        const matched = clients.find((c) => c.url === targetUrl)
        return matched ? matched.focus() : self.clients.openWindow(targetUrl)
      })
  )
})
