import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/v1'),
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('Proxy error:', err.message)
          })
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('Proxy request:', req.method, req.url, '->', proxyReq.path)
          })
        }
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true
  }
})