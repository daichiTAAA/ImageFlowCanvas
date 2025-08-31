#!/bin/bash

# Docker Compose setup script for ImageFlowCanvas
#
# Usage:
#   ./scripts/run-compose.sh                    # Start all services
#   ./scripts/run-compose.sh build             # Build and start services
#   ./scripts/run-compose.sh dev               # Start development environment with hot reload
#   ./scripts/run-compose.sh stop              # Stop all services
#   ./scripts/run-compose.sh down              # Stop and remove services
#   ./scripts/run-compose.sh logs              # Show logs
#   ./scripts/run-compose.sh status            # Show service status

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_DIR="$BASE_DIR/deploy/compose"
ACTION=${1:-"up"}

echo "🐳 ImageFlowCanvas Docker Compose Management"
echo "Base Directory: $BASE_DIR"
echo "Compose Directory: $COMPOSE_DIR"
echo "Action: $ACTION"

cd "$COMPOSE_DIR"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

case "$ACTION" in
    "up" | "start")
        echo "🚀 Starting ImageFlowCanvas services..."
        docker compose up -d
        echo "✅ Services started successfully!"
        echo ""
        echo "🌐 Access points:"
        echo "  - Web UI: http://localhost:3000"
        echo "  - Backend API: http://localhost:8000/docs"
        echo "  - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
        echo "  - gRPC Gateway: http://localhost:8080/health"
        echo "  - Kafka: localhost:9094"
        echo "  - MediaMTX HLS: http://localhost:8888/{path}/index.m3u8"
        echo "  - MediaMTX API: http://localhost:9997/v3/paths/list"
        echo ""
        echo "📊 Service status:"
        docker compose ps
        ;;
    
    "dev")
        echo "🚀 Starting ImageFlowCanvas Development Environment..."
        echo "🔄 Hot reload enabled for web UI changes"
        
        # Stop any existing containers
        echo "🛑 Stopping existing containers..."
        docker compose -f docker-compose.yml -f docker-compose.dev.yml down

        echo "🔨 Building and starting ImageFlowCanvas services..."
        
        # Build services first
        echo "📦 Building Docker images..."
        cd "$BASE_DIR"
        ./scripts/build_services.sh
        
        # Start services
        cd "$COMPOSE_DIR"
        
        # Build and start development environment
        echo "🔨 Building and starting development environment..."
        docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
        
        echo "✅ Development environment started!"
        echo "📱 Web UI: http://localhost:3000"
        echo "🔄 Hot reload is enabled - changes to web/src/ files will automatically reload"
        echo ""
        echo "To stop the environment, press Ctrl+C or run:"
        echo "$0 down"
        ;;
    
    "build")
        echo "🔨 Building and starting ImageFlowCanvas services..."
        
        # Build services first
        echo "📦 Building Docker images..."
        cd "$BASE_DIR"
        ./scripts/build_services.sh
        
        # Start services
        cd "$COMPOSE_DIR"
        docker compose up -d
        echo "✅ Services built and started successfully!"
        
        echo ""
        echo "🌐 Access points:"
        echo "  - Web UI: http://localhost:3000"
        echo "  - Backend API: http://localhost:8000/docs"
        echo "  - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
        echo "  - gRPC Gateway: http://localhost:8080/health"
        echo "  - Kafka: localhost:9094"
        echo "  - MediaMTX HLS: http://localhost:8888/{path}/index.m3u8"
        echo "  - MediaMTX API: http://localhost:9997/v3/paths/list"
        ;;
    
    "stop")
        echo "⏹️  Stopping ImageFlowCanvas services..."
        docker compose stop
        echo "✅ Services stopped successfully!"
        ;;
    
    "down")
        echo "🗑️  Stopping and removing ImageFlowCanvas services..."
        # Check if development compose file exists and use it if needed
        if [ -f "docker-compose.dev.yml" ]; then
            docker compose -f docker-compose.yml -f docker-compose.dev.yml down
        else
            docker compose down
        fi
        echo "✅ Services stopped and removed successfully!"
        echo ""
        echo "💾 To remove persistent data, run:"
        echo "   docker volume rm compose_postgres_data compose_minio_data"
        ;;

    "logs")
        echo "📋 Showing ImageFlowCanvas service logs..."
        # Check if development compose file exists and use it if needed
        if [ -f "docker-compose.dev.yml" ] && docker compose -f docker-compose.yml -f docker-compose.dev.yml ps | grep -q "Up"; then
            docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f
        else
            docker compose logs -f
        fi
        ;;

    "status" | "ps")
        echo "📊 ImageFlowCanvas service status:"
        # Check if development compose file exists and show dev status if running
        if [ -f "docker-compose.dev.yml" ] && docker compose -f docker-compose.yml -f docker-compose.dev.yml ps | grep -q "Up"; then
            echo "🔧 Development environment:"
            docker compose -f docker-compose.yml -f docker-compose.dev.yml ps
        else
            docker compose ps
        fi
        ;;

    "restart")
        echo "🔄 Restarting ImageFlowCanvas services..."
        # Check if development compose file exists and use it if needed
        if [ -f "docker-compose.dev.yml" ] && docker compose -f docker-compose.yml -f docker-compose.dev.yml ps | grep -q "Up"; then
            docker compose -f docker-compose.yml -f docker-compose.dev.yml restart
        else
            docker compose restart
        fi
        echo "✅ Services restarted successfully!"
        ;;
    
    "pull")
        echo "📥 Pulling latest images..."
        docker compose pull
        echo "✅ Images updated successfully!"
        ;;
    
    "health")
        echo "🏥 Checking service health..."
        echo ""
        
        # Check core services
        echo "🔍 Infrastructure services:"
        curl -f http://localhost:5432 && echo "✅ PostgreSQL: Running" || echo "❌ PostgreSQL: Down"
        curl -f http://localhost:9000/minio/health/live && echo "✅ MinIO: Running" || echo "❌ MinIO: Down"
        
        echo ""
        echo "🔍 Application services:"
        curl -f http://localhost:8000/v1/health && echo "✅ Backend: Running" || echo "❌ Backend: Down"
        curl -f http://localhost:3000 && echo "✅ Web UI: Running" || echo "❌ Web UI: Down"
        curl -f http://localhost:8080/health && echo "✅ gRPC Gateway: Running" || echo "❌ gRPC Gateway: Down"
        ;;
    
    *)
        echo "❓ Usage: $0 {up|build|dev|stop|down|logs|status|restart|pull|health}"
        echo ""
        echo "Commands:"
        echo "  up/start  - Start all services (production mode)"
        echo "  build     - Build and start services (production mode)"
        echo "  dev       - Start development environment with hot reload"
        echo "  stop      - Stop all services"
        echo "  down      - Stop and remove services"
        echo "  logs      - Show service logs"
        echo "  status/ps - Show service status"
        echo "  restart   - Restart all services"
        echo "  pull      - Pull latest images"
        echo "  health    - Check service health"
        exit 1
        ;;
esac
