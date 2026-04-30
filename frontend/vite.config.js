import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  const devServerPort = env.VITE_DEV_PORT
    ? Number(env.VITE_DEV_PORT)
    : 5173

  return {
    plugins: [
      react(),
      VitePWA({
        registerType: 'autoUpdate',
        filename: 'manifest.json',
        devOptions: {
          enabled: true,
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
              src: 'favicons/android-chrome-192x192.png',
              sizes: '192x192',
              type: 'image/png',
              purpose: 'any',
            },
            {
              src: 'favicons/android-chrome-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              purpose: 'any',
            },
          ],
          screenshots: [
            {
              src: 'favicons/android-chrome-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              form_factor: 'wide',
              label: 'Care-full 대시보드',
            },
            {
              src: 'favicons/android-chrome-512x512.png',
              sizes: '512x512',
              type: 'image/png',
              label: 'Care-full 모바일',
            },
          ],
        },
        workbox: {
          globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
          navigateFallback: 'index.html',
          runtimeCaching: [
            {
              urlPattern: ({ request }) => request.destination === 'document',
              handler: 'NetworkFirst',
              options: {
                cacheName: 'pages-cache',
                expiration: {
                  maxEntries: 10,
                  maxAgeSeconds: 60 * 60 * 24,
                },
              },
            },
            {
              urlPattern: ({ request }) =>
                ['style', 'script', 'worker'].includes(request.destination),
              handler: 'StaleWhileRevalidate',
              options: {
                cacheName: 'assets-cache',
              },
            },
            {
              urlPattern: ({ request }) => request.destination === 'image',
              handler: 'StaleWhileRevalidate',
              options: {
                cacheName: 'image-cache',
                expiration: {
                  maxEntries: 50,
                  maxAgeSeconds: 60 * 60 * 24 * 30,
                },
              },
            },
          ],
        },
      }),
    ],
    server: {
      host: env.VITE_DEV_HOST || '0.0.0.0',
      port: devServerPort,
      strictPort: true
    },
  }
})