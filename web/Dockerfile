# Build stage
FROM node:18-alpine AS build

# プロキシ設定を引き継ぎ
ARG PROXY
ENV PROXY=$PROXY

WORKDIR /app

# Copy package files
COPY web/package.json web/package-lock.json ./

# Configure npm proxy settings
RUN if [ -n "$PROXY" ]; then \
    npm config set proxy $PROXY && \
    npm config set https-proxy $PROXY && \
    npm config set registry https://registry.npmjs.org/; \
    fi

# Install dependencies (fallback to npm install when lock is out of sync)
RUN npm ci || npm install --no-audit --no-fund

# Copy source code
COPY web/ .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Install envsubst for environment variable substitution
RUN apk add --no-cache gettext

# Copy custom nginx config template
COPY web/nginx.conf.template /etc/nginx/nginx.conf.template

# Copy startup script
COPY web/start-nginx.sh /start-nginx.sh
RUN chmod +x /start-nginx.sh

# Copy built application
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port 3000
EXPOSE 3000

ENV no_proxy="localhost,0.0.0.0"
ENV NO_PROXY=${no_proxy}

CMD ["/start-nginx.sh"]
