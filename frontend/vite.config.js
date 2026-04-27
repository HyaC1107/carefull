import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import process from 'node:process'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const devServerPort = env.VITE_DEV_PORT
    ? Number(env.VITE_DEV_PORT)
    : undefined

  return {
    plugins: [react()],
    server: {
      host: env.VITE_DEV_HOST || undefined,
      port: devServerPort,
      strictPort: Boolean(devServerPort),
    },
  }
})
