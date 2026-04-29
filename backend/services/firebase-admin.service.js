const admin = require('firebase-admin');

let firebase_app = null;

const get_firebase_app = () => {
    if (firebase_app) {
        return firebase_app;
    }

    const {
        FIREBASE_PROJECT_ID,
        FIREBASE_CLIENT_EMAIL,
        FIREBASE_PRIVATE_KEY
    } = process.env;

    if (!FIREBASE_PROJECT_ID || !FIREBASE_CLIENT_EMAIL || !FIREBASE_PRIVATE_KEY) {
        throw new Error('Missing Firebase Admin env variables.');
    }

    firebase_app = admin.initializeApp({
        credential: admin.credential.cert({
            projectId: FIREBASE_PROJECT_ID,
            clientEmail: FIREBASE_CLIENT_EMAIL,
            privateKey: FIREBASE_PRIVATE_KEY.replace(/\\n/g, '\n')
        })
    });

    return firebase_app;
};

const get_messaging = () => admin.messaging(get_firebase_app());

module.exports = {
    get_messaging
};
