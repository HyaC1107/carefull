import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const swPath = path.join(__dirname, 'public', 'firebase-messaging-sw.js');

if (fs.existsSync(swPath)) {
  let content = fs.readFileSync(swPath, 'utf8');

  const envVars = [
    'VITE_FIREBASE_API_KEY',
    'VITE_FIREBASE_AUTH_DOMAIN',
    'VITE_FIREBASE_PROJECT_ID',
    'VITE_FIREBASE_STORAGE_BUCKET',
    'VITE_FIREBASE_MESSAGING_SENDER_ID',
    'VITE_FIREBASE_APP_ID'
  ];

  envVars.forEach(varName => {
    const value = process.env[varName] || '';
    const placeholder = `__${varName}__`;
    content = content.replaceAll(placeholder, value);
    console.log(`[FCM-BUILD] Injected ${varName}`);
  });

  fs.writeFileSync(swPath, content);
  console.log('[FCM-BUILD] firebase-messaging-sw.js updated with environment variables.');
} else {
  console.error('[FCM-BUILD] firebase-messaging-sw.js not found at', swPath);
}
