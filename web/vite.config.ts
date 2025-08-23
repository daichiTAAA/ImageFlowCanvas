import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    // Ensure HMR client doesn't try ws://0.0.0.0:xxxx in browsers
    // Default to localhost; allow override via env for docker-compose
    hmr: {
      host: process.env.HMR_HOST || 'localhost',
      // If provided, use an explicit HMR port (e.g., 3001) used by proxy
      port: process.env.HMR_PORT ? Number(process.env.HMR_PORT) : undefined,
    },
    // Nginxでプロキシするため、Viteのプロキシ設定は削除
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})
