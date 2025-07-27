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
npm run dev:nginx -- --host 0.0.0.0 --port 3001 &
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
