import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Determine backend target based on environment
// In Docker: VITE_BACKEND_URL is set to http://backend:8000
// In local development: Use localhost:8000
const getBackendTarget = () => {
  const envUrl = process.env.VITE_BACKEND_URL
  
  // If VITE_BACKEND_URL contains 'backend:8000', we're likely in Docker
  // For local development, always use localhost
  if (envUrl && envUrl.includes('backend:8000')) {
    // Check if we're actually running in Docker by looking for Docker-specific indicators
    // If not, fallback to localhost
    const isDocker = process.env.DOCKER_ENV === 'true' || process.env.NODE_ENV === 'docker'
    return isDocker ? envUrl : 'http://localhost:8000'
  }
  
  return envUrl || 'http://localhost:8000'
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