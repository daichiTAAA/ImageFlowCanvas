#!/bin/sh

# Development startup script for nginx + Vite
# This script starts both nginx and Vite dev server for hot reload support

set -e

echo "🚀 Starting development environment..."

# Set default values for environment variables if not provided
export BACKEND_HOST=${BACKEND_HOST:-backend}
export BACKEND_PORT=${BACKEND_PORT:-8000}
export NGINX_RESOLVER=${NGINX_RESOLVER:-}

# Process nginx configuration template
echo "📝 Processing nginx configuration..."
envsubst '${BACKEND_HOST} ${BACKEND_PORT} ${NGINX_RESOLVER}' < /etc/nginx/nginx.dev.conf.template > /etc/nginx/nginx.conf

# Start Vite dev server in background
echo "🔥 Starting Vite dev server on port 3001..."
# Allow overriding HMR public host/port if developing remotely
export HMR_HOST=${HMR_HOST:-localhost}
export HMR_CLIENT_PORT=${HMR_CLIENT_PORT:-3000}
export HMR_PROTOCOL=${HMR_PROTOCOL:-ws}
export HMR_ORIGIN=${HMR_ORIGIN:-http://localhost:3000}
echo "HMR public endpoint: ${HMR_PROTOCOL}://${HMR_HOST}:${HMR_CLIENT_PORT} (origin ${HMR_ORIGIN})"

# Use Vite config for host/port to avoid leaking 0.0.0.0 to client HMR URL
npm run dev:nginx &
VITE_PID=$!

# Wait for Vite to start
echo "⏳ Waiting for Vite dev server to start..."
sleep 5

# Check if Vite is running
if ! kill -0 $VITE_PID 2>/dev/null; then
    echo "❌ Failed to start Vite dev server"
    exit 1
fi

echo "✅ Vite dev server started successfully"

# Start nginx in foreground
echo "🌐 Starting nginx on port 3000..."
exec nginx -g 'daemon off;'
