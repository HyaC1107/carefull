// Firebase Messaging 백그라운드 푸시 수신 서비스 워커
// firebase.js와 동일한 설정값으로 채워야 합니다.
// 서비스 워커는 Vite 번들링 밖에 있으므로 env 변수를 직접 사용할 수 없습니다.
// Firebase 콘솔 → 프로젝트 설정 → 일반 → 웹 앱 구성에서 값 확인 후 기입하세요.

importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey:            '__VITE_FIREBASE_API_KEY__',
  authDomain:        '__VITE_FIREBASE_AUTH_DOMAIN__',
  projectId:         '__VITE_FIREBASE_PROJECT_ID__',
  storageBucket:     '__VITE_FIREBASE_STORAGE_BUCKET__',
  messagingSenderId: '__VITE_FIREBASE_MESSAGING_SENDER_ID__',
  appId:             '__VITE_FIREBASE_APP_ID__',
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
