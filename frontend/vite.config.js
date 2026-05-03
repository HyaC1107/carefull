import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import path from 'node:path'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const isDevelopment = mode === 'development'

  const devServerPort = env.VITE_DEV_PORT
    ? Number(env.VITE_DEV_PORT)
    : undefined

  const resolveEnvPath = (value) => (
    value && (path.isAbsolute(value) ? value : path.resolve(process.cwd(), value))
  )

  const sslKeyPath = resolveEnvPath(env.SSL_KEY_PATH)
  const sslCertPath = resolveEnvPath(env.SSL_CERT_PATH)
  const hasDevHttpsCerts = Boolean(
    isDevelopment
    && sslKeyPath
    && sslCertPath
    && fs.existsSync(sslKeyPath)
    && fs.existsSync(sslCertPath)
  )

  const devServer = {
    strictPort: Boolean(devServerPort),
    ...(env.VITE_DEV_HOST ? { host: env.VITE_DEV_HOST } : {}),
    ...(devServerPort ? { port: devServerPort } : {}),
    ...(env.VITE_ALLOWED_HOSTS
      ? { allowedHosts: env.VITE_ALLOWED_HOSTS.split(',').map((host) => host.trim()).filter(Boolean) }
      : {}),
    ...(hasDevHttpsCerts
      ? {
          https: {
            key: fs.readFileSync(sslKeyPath),
            cert: fs.readFileSync(sslCertPath),
          },
        }
      : {}),
  }

  return {
    plugins: [
      react(),
      VitePWA({
        registerType: 'autoUpdate',
        strategies: 'injectManifest',
        srcDir: 'src',
        filename: 'sw.js',
        devOptions: {
          enabled: true,
          type: 'module',
        },
        includeAssets: [
          'favicons/favicon.ico',
          'favicons/android-chrome-192x192.png',
          'favicons/android-chrome-512x512.png',
        ],
        manifest: {
          id: '/',
          name: 'Care-full',
          short_name: 'Care-full',
          description: '케어풀 - 스마트 복약 관리 서비스',
          theme_color: '#1f3b73',
          background_color: '#ffffff',
          display: 'standalone',
          start_url: '/login',
          scope: '/',
          icons: [
            {
              src: '/favicons/android-chrome-192x192.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'any maskable',
            },
            {
              src: '/favicons/android-chrome-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any maskable',
            },
          ],
          screenshots: [
            {
              src: '/favicons/android-chrome-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              form_factor: 'wide',
              label: 'Care-full 대시보드',
            },
            {
              src: '/favicons/android-chrome-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              label: 'Care-full 모바일',
            },
          ],
        },
        injectManifest: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
          globIgnores: ['firebase-messaging-sw.js'],
        },
      }),
    ],
    server: devServer,
  }
})
