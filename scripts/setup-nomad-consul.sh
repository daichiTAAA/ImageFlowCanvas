#!/bin/bash

# Setup script for Nomad and Consul development environment
#
# Usage:
#   ./scripts/setup-nomad-consul.sh                # Full setup
#   ./scripts/setup-nomad-consul.sh deploy         # Deploy jobs only (requires running cluster)
#   ./scripts/setup-nomad-consul.sh stop           # Stop all jobs
#   ./scripts/setup-nomad-consul.sh status         # Show job status

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NOMAD_DIR="$BASE_DIR/deploy/nomad"
ACTION=${1:-"setup"}

echo "🏗️ ImageFlowCanvas Nomad/Consul Management"
echo "Base Directory: $BASE_DIR"
echo "Nomad Directory: $NOMAD_DIR"
echo "Action: $ACTION"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to wait for service to be ready
wait_for_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for $service_name to be ready on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "http://localhost:$port" >/dev/null 2>&1; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        
        echo "  Attempt $attempt/$max_attempts - $service_name not ready yet..."
        sleep 5
        attempt=$((attempt + 1))
    done
    
    echo "❌ $service_name failed to become ready after $max_attempts attempts"
    return 1
}

case "$ACTION" in
    "setup")
        echo "🚀 Setting up Nomad and Consul environment..."
        
        # Check if running on Linux
        if [[ "$OSTYPE" != "linux-gnu"* ]]; then
            echo "Warning: This script is designed for Linux. For other platforms, please install Nomad and Consul manually."
        fi
        
        # Install Consul if not already installed
        if ! command_exists consul; then
            echo "📦 Installing Consul..."
            wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
            echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
            sudo apt update && sudo apt install consul
        else
            echo "✅ Consul is already installed"
        fi
        
        # Install Nomad if not already installed
        if ! command_exists nomad; then
            echo "📦 Installing Nomad..."
            sudo apt install nomad
        else
            echo "✅ Nomad is already installed"
        fi
        
        # Start Consul in development mode
        echo "🏃 Starting Consul in development mode..."
        consul agent -dev -client=0.0.0.0 -bind=127.0.0.1 &
        CONSUL_PID=$!
        
        # Wait for Consul to be ready
        wait_for_service "Consul" "8500"
        
        # Start Nomad in development mode
        echo "🏃 Starting Nomad in development mode..."
        sudo nomad agent -dev -bind=0.0.0.0 -consul-address=127.0.0.1:8500 &
        NOMAD_PID=$!
        
        # Wait for Nomad to be ready  
        wait_for_service "Nomad" "4646"
        
        # Set environment variables
        export NOMAD_ADDR=http://localhost:4646
        export CONSUL_HTTP_ADDR=http://localhost:8500
        
        echo "✅ Nomad and Consul are running!"
        echo ""
        echo "🌐 Access points:"
        echo "  - Nomad UI: http://localhost:4646"
        echo "  - Consul UI: http://localhost:8500"
        echo ""
        
        # Deploy ImageFlowCanvas services
        echo "🚀 Deploying ImageFlowCanvas services..."
        $0 deploy
        ;;
    
    "deploy")
        echo "📦 Deploying ImageFlowCanvas to Nomad..."
        
        # Set environment variables
        export NOMAD_ADDR=http://localhost:4646
        export CONSUL_HTTP_ADDR=http://localhost:8500
        
        # Build services first
        echo "🔨 Building Docker images..."
        cd "$BASE_DIR"
        ./scripts/build_services.sh
        
        # Deploy infrastructure services
        echo "🏗️ Deploying infrastructure services..."
        nomad job run "$NOMAD_DIR/infrastructure.nomad"
        
        # Wait for infrastructure to be ready
        echo "⏳ Waiting for infrastructure services to be ready..."
        sleep 30
        
        # Deploy gRPC services
        echo "🔧 Deploying gRPC services..."
        nomad job run "$NOMAD_DIR/grpc-services.nomad"
        
        # Wait for gRPC services to be ready
        echo "⏳ Waiting for gRPC services to be ready..."
        sleep 20
        
        # Deploy application services
        echo "🌐 Deploying application services..."
        nomad job run "$NOMAD_DIR/application.nomad"
        
        echo "✅ All services deployed successfully!"
        echo ""
        echo "🌐 Access points:"
        echo "  - Frontend: http://localhost:3000"
        echo "  - Backend API: http://localhost:8000/docs"
        echo "  - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
        echo "  - gRPC Gateway: http://localhost:8080/health"
        echo "  - Nomad UI: http://localhost:4646"
        echo "  - Consul UI: http://localhost:8500"
        ;;
    
    "stop")
        echo "⏹️ Stopping ImageFlowCanvas services..."
        
        export NOMAD_ADDR=http://localhost:4646
        
        # Stop all jobs
        nomad job stop imageflow-application
        nomad job stop imageflow-grpc-services  
        nomad job stop imageflow-infrastructure
        
        echo "✅ All services stopped successfully!"
        ;;
    
    "status")
        echo "📊 ImageFlowCanvas service status:"
        
        export NOMAD_ADDR=http://localhost:4646
        
        echo ""
        echo "🏗️ Infrastructure:"
        nomad job status imageflow-infrastructure
        
        echo ""
        echo "🔧 gRPC Services:"
        nomad job status imageflow-grpc-services
        
        echo ""
        echo "🌐 Application:"
        nomad job status imageflow-application
        ;;
    
    "logs")
        echo "📋 Showing service logs..."
        
        export NOMAD_ADDR=http://localhost:4646
        
        echo "Select a service to view logs:"
        echo "1. Infrastructure"
        echo "2. gRPC Services"
        echo "3. Application"
        read -p "Enter choice (1-3): " choice
        
        case $choice in
            1) nomad alloc logs -job imageflow-infrastructure ;;
            2) nomad alloc logs -job imageflow-grpc-services ;;
            3) nomad alloc logs -job imageflow-application ;;
            *) echo "Invalid choice" ;;
        esac
        ;;
    
    "health")
        echo "🏥 Checking service health..."
        
        echo ""
        echo "🔍 Infrastructure services:"
        curl -f http://localhost:5432 && echo "✅ PostgreSQL: Running" || echo "❌ PostgreSQL: Down"
        curl -f http://localhost:9000/minio/health/live && echo "✅ MinIO: Running" || echo "❌ MinIO: Down"
        
        echo ""
        echo "🔍 Application services:"
        curl -f http://localhost:8000/v1/health && echo "✅ Backend: Running" || echo "❌ Backend: Down"
        curl -f http://localhost:3000 && echo "✅ Frontend: Running" || echo "❌ Frontend: Down"
        curl -f http://localhost:8080/health && echo "✅ gRPC Gateway: Running" || echo "❌ gRPC Gateway: Down"
        ;;
    
    *)
        echo "❓ Usage: $0 {setup|deploy|stop|status|logs|health}"
        echo ""
        echo "Commands:"
        echo "  setup   - Install and setup Nomad/Consul environment"
        echo "  deploy  - Deploy ImageFlowCanvas services"
        echo "  stop    - Stop all services"
        echo "  status  - Show job status"
        echo "  logs    - Show service logs"
        echo "  health  - Check service health"
        exit 1
        ;;
esac