#!/bin/sh

# Default values
BACKEND_HOST=${BACKEND_HOST:-"backend"}
BACKEND_PORT=${BACKEND_PORT:-"8000"}
NGINX_RESOLVER=${NGINX_RESOLVER:-""}

echo "Configuring nginx for environment:"
echo "BACKEND_HOST: $BACKEND_HOST"
echo "BACKEND_PORT: $BACKEND_PORT"
echo "NGINX_RESOLVER: $NGINX_RESOLVER"

# Replace environment variables in nginx.conf.template
envsubst '${BACKEND_HOST} ${BACKEND_PORT} ${NGINX_RESOLVER}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

echo "Generated nginx.conf:"
cat /etc/nginx/nginx.conf

# Start nginx
exec nginx -g "daemon off;"
