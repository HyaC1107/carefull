import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      includeAssets: ['favicons.ico', 'apple-touch-icon.png', 'mask-icon.svg'],
      manifest: {
        name: 'CARE-FULL: 스마트 복약 관리',
        short_name: 'CARE-FULL',
        description: 'AI로 복약 여부를 확인하는 스마트 헬스케어 시스템',
        theme_color: '#2e7d32',
        background_color: '#ffffff',
        display: 'standalone',
        icons: [
          {
            src: 'favicons/android-chrome-192x192.png',
            sizes: '192x192',
            type: 'image/png',
          },
          {
            src: 'favicons/android-chrome-512x512.png',
            sizes: '512x512',
            type: 'image/png',
          },
          {
            src: 'favicons/android-chrome-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ]
      },
      devOptions: {
        enabled: true
      }
    })
  ],
})
