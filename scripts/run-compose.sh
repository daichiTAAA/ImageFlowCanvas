#!/bin/bash

# Docker Compose setup script for ImageFlowCanvas
#
# Usage:
#   ./scripts/run-compose.sh                    # Start all services
#   ./scripts/run-compose.sh build             # Build and start services
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
        echo ""
        echo "📊 Service status:"
        docker compose ps
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
        ;;
    
    "stop")
        echo "⏹️  Stopping ImageFlowCanvas services..."
        docker compose stop
        echo "✅ Services stopped successfully!"
        ;;
    
    "down")
        echo "🗑️  Stopping and removing ImageFlowCanvas services..."
        docker compose down
        echo "✅ Services stopped and removed successfully!"
        echo ""
        echo "💾 To remove persistent data, run:"
        echo "   docker volume rm compose_postgres_data compose_minio_data"
        ;;
    
    "logs")
        echo "📋 Showing ImageFlowCanvas service logs..."
        docker compose logs -f
        ;;
    
    "status" | "ps")
        echo "📊 ImageFlowCanvas service status:"
        docker compose ps
        ;;
    
    "restart")
        echo "🔄 Restarting ImageFlowCanvas services..."
        docker compose restart
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
        echo "❓ Usage: $0 {up|build|stop|down|logs|status|restart|pull|health}"
        echo ""
        echo "Commands:"
        echo "  up/start  - Start all services"
        echo "  build     - Build and start services"
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