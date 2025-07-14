import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    // Nginxでプロキシするため、Viteのプロキシ設定は削除
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})