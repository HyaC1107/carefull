const admin = require('firebase-admin');

let _initialized = false;

const _init = () => {
    if (_initialized) return true;

    const sa_json = process.env.FIREBASE_SERVICE_ACCOUNT;
    const project_id = process.env.FIREBASE_PROJECT_ID;

    if (!sa_json || !project_id) {
        return false;
    }

    try {
        const service_account = JSON.parse(sa_json);
        admin.initializeApp({
            credential: admin.credential.cert(service_account),
            projectId: project_id,
        });
        _initialized = true;
        return true;
    } catch (e) {
        console.error('[FCM] init failed:', e.message);
        return false;
    }
};

// 서버 시작 시 초기화 시도
_init();

const send_push = async (fcm_token, title, body) => {
    if (!_initialized && !_init()) return false;
    if (!fcm_token) return false;

    try {
        await admin.messaging().send({
            token: fcm_token,
            notification: { title, body },
            webpush: {
                notification: {
                    title,
                    body,
                    icon: '/favicons/favicon.ico',
                    badge: '/favicons/favicon.ico',
                },
            },
        });
        return true;
    } catch (e) {
        console.error('[FCM] send_push failed:', e.message);
        return false;
    }
};

module.exports = { send_push };
