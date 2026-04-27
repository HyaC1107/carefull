self.addEventListener('push', (event) => {
  const payload = event.data ? event.data.json() : {}
  const notification = payload.notification || {}
  const data = payload.data || {}
  const title = notification.title || data.title || 'Carefull'
  const options = {
    body: notification.body || data.body || '',
    data,
  }

  event.waitUntil(self.registration.showNotification(title, options))
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
