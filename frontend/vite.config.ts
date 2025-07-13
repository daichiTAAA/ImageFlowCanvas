import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Determine backend target based on environment
// In Docker: VITE_BACKEND_URL is set to http://backend:8000
// In local development: Use localhost:8000
const getBackendTarget = () => {
  const envUrl = process.env.VITE_BACKEND_URL
  
  // If VITE_BACKEND_URL is set, use it directly
  // This handles both Docker (backend:8000) and local development properly
  if (envUrl) {
    return envUrl
  }
  
  // Fallback to localhost for local development
  return 'http://localhost:8000'
}

const backendTarget = getBackendTarget()

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: backendTarget,
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