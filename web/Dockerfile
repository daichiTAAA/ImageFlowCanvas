# Build stage
FROM node:18-alpine AS build

WORKDIR /app

# Copy package files
COPY web/package.json web/package-lock.json ./

# Install dependencies
RUN npm ci

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

CMD ["/start-nginx.sh"]