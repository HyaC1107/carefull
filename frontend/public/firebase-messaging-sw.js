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
// Firebase Messaging 백그라운드 푸시 수신 서비스 워커
// firebase.js와 동일한 설정값으로 채워야 합니다.
// 서비스 워커는 Vite 번들링 밖에 있으므로 env 변수를 직접 사용할 수 없습니다.
// Firebase 콘솔 → 프로젝트 설정 → 일반 → 웹 앱 구성에서 값 확인 후 기입하세요.

importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey:            'AIzaSyBWZpQ5hT6acwWmemzJcrD5K2JrTgEvVJk',
  authDomain:        'carefull-b93c0.firebaseapp.com',
  projectId:         'carefull-b93c0',
  messagingSenderId: '234144601113',
  appId:             '1:234144601113:web:3b172e4bf309ee9196c688',
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  const title = payload?.notification?.title || 'CARE-FULL 알림';
  const body  = payload?.notification?.body  || '';
  self.registration.showNotification(title, {
    body,
    icon: '/favicons/favicon.ico',
    badge: '/favicons/favicon.ico',
  });
});
