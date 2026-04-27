import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'node:fs'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    https: {
      key: fs.readFileSync('../backend/192.168.219.225.nip.io-key.pem'),
      cert: fs.readFileSync('../backend/192.168.219.225.nip.io.pem'),
    },
  },
})
