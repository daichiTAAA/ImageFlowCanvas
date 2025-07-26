#!/bin/bash

# Setup script for Nomad and Consul development environment
#
# Usage:
#   ./scripts/setup-nomad-consul.sh                # Full setup (install & start Nomad/Consul + deploy services)
#   ./scripts/setup-nomad-consul.sh deploy         # Deploy jobs only (requires running cluster)
#   ./scripts/setup-nomad-consul.sh stop           # Stop all jobs
#   ./scripts/setup-nomad-consul.sh status         # Show job status
#   ./scripts/setup-nomad-consul.sh logs           # Show service logs (interactive)
#   ./scripts/setup-nomad-consul.sh health         # Check service health endpoints
#   ./scripts/setup-nomad-consul.sh kill           # Kill Nomad and Consul background processes

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

# Function to optimize Docker for large image pulls
optimize_docker() {
    echo "🐳 Optimizing Docker configuration for large image pulls..."
    
    # Create or update Docker daemon configuration
    local docker_config_dir="/etc/docker"
    local docker_config_file="$docker_config_dir/daemon.json"
    
    if [ ! -d "$docker_config_dir" ]; then
        sudo mkdir -p "$docker_config_dir"
    fi
    
    # Backup existing config if it exists
    if [ -f "$docker_config_file" ]; then
        sudo cp "$docker_config_file" "$docker_config_file.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Create optimized Docker daemon configuration
    sudo tee "$docker_config_file" > /dev/null << EOF
{
  "max-concurrent-downloads": 3,
  "max-concurrent-uploads": 5,
  "max-download-attempts": 5,
  "registry-mirrors": [],
  "insecure-registries": [],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
    
    echo "✅ Docker configuration optimized"
    echo "ℹ️  Note: Docker daemon restart may be required for changes to take effect"
}

# Function to wait for service to be ready
wait_for_service() {
    local service_name=$1
    local port=$2
    local max_attempts=5
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

# Function to setup Nomad configuration
setup_nomad_config() {
    local config_file="$NOMAD_DIR/nomad.hcl"
    local base_dir="$BASE_DIR"
    
    # Create the configuration file with dynamic paths
    cat > "$config_file" << EOF
# Nomad development configuration for ImageFlowCanvas
datacenter = "dc1"
data_dir = "/tmp/nomad"

# Bind configuration
bind_addr = "0.0.0.0"

# Server configuration
server {
  enabled = true
  bootstrap_expect = 1
  
  # ACL and encryption disabled for development
  encrypt = ""
}

# Client configuration  
client {
  enabled = true
  node_class = "compute"
  
  # Force specific CPU total for virtual environments
  cpu_total_compute = 4000
  
  # Reserved resources
  reserved {
    cpu    = 200
    memory = 512
  }
  
  # Host volumes configuration for data persistence
  host_volume "postgres_data" {
    path      = "/opt/nomad/volumes/postgres_data"
    read_only = false
  }
  
  host_volume "minio_data" {
    path      = "/opt/nomad/volumes/minio_data"
    read_only = false
  }
  
  host_volume "redis_data" {
    path      = "/opt/nomad/volumes/redis_data"
    read_only = false
  }
  
  host_volume "kafka_data" {
    path      = "/opt/nomad/volumes/kafka_data"
    read_only = false
  }
  
  host_volume "models_data" {
    path      = "${base_dir}/models"
    read_only = true
  }
}

# Consul integration
consul {
  address = "127.0.0.1:8500"
}

# Plugins
plugin "docker" {
  config {
    allow_privileged = false
    allow_caps = ["audit_write", "chown", "dac_override", "fowner", "fsetid", "kill", "mknod", "net_bind_service", "setfcap", "setgid", "setpcap", "setuid", "sys_chroot"]
  }
}

# Telemetry
telemetry {
  collection_interval = "1s"
  disable_hostname = true
  prometheus_metrics = true
  publish_allocation_metrics = true
  publish_node_metrics = true
}

# Ports
ports {
  http = 4646
  rpc  = 4647
  serf = 4648
}
EOF
    
    echo "$config_file"
}

# Function to setup host volumes for Nomad
setup_host_volumes() {
    echo "📁 Setting up host volumes for Nomad..."
    
    local volumes=(
        "/opt/nomad/volumes/postgres_data"
        "/opt/nomad/volumes/minio_data"
        "/opt/nomad/volumes/redis_data"
        "/opt/nomad/volumes/kafka_data"
    )
    
    for volume in "${volumes[@]}"; do
        if [ ! -d "$volume" ]; then
            echo "  Creating volume: $volume"
            sudo mkdir -p "$volume"
            sudo chown -R $(whoami):$(whoami) "$volume"
            sudo chmod 755 "$volume"
        else
            echo "  Volume already exists: $volume"
        fi
    done
    
    echo "✅ Host volumes setup completed"
}

# Function to cleanup background processes
cleanup_processes() {
    echo "🧹 Cleaning up background processes..."
    
    # Kill Consul and Nomad processes
    pkill -f "consul agent" || true
    pkill -f "nomad agent" || true
    
    # Wait a bit for graceful shutdown
    sleep 2
    
    # Force kill if still running
    pkill -9 -f "consul agent" || true
    pkill -9 -f "nomad agent" || true
    
    echo "✅ Background processes cleaned up"
}

case "$ACTION" in
    "setup")
        echo "🚀 Setting up Nomad and Consul environment..."
        
        # Check if running on Linux
        if [[ "$OSTYPE" != "linux-gnu"* ]]; then
            echo "Warning: This script is designed for Linux. For other platforms, please install Nomad and Consul manually."
        fi
        
        # Optimize Docker configuration for large image pulls
        optimize_docker
        
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
        
        # Setup host volumes for Nomad
        setup_host_volumes
        
        # Start Consul in development mode
        echo "🏃 Starting Consul with configuration..."
        CONSUL_CONFIG="$NOMAD_DIR/consul.hcl"
        if [ -f "$CONSUL_CONFIG" ]; then
            consul agent -config-file="$CONSUL_CONFIG" &
        else
            echo "⚠️ Consul config not found, using dev mode"
            consul agent -dev -client=0.0.0.0 -bind=127.0.0.1 &
        fi
        CONSUL_PID=$!
        
        # Wait for Consul to be ready
        wait_for_service "Consul" "8500"
        
        # Start Nomad in development mode
        echo "🏃 Starting Nomad in development mode..."
        CPU_CORES=$(nproc)
        echo "  Detected ${CPU_CORES} CPU cores"
        
        # Create Nomad configuration and start with it
        echo "📝 Setting up Nomad configuration..."
        NOMAD_CONFIG=$(setup_nomad_config)
        if [ $? -ne 0 ]; then
            echo "❌ Failed to setup Nomad configuration"
            exit 1
        fi
        echo "✅ Nomad configuration generated at: $NOMAD_CONFIG"
        sudo nomad agent -config="$NOMAD_CONFIG" -bind=0.0.0.0 &
        NOMAD_PID=$!
        
        # Wait for Nomad to be ready  
        wait_for_service "Nomad" "4646"
        
        # Set environment variables
        export NOMAD_ADDR=http://localhost:4646
        export CONSUL_HTTP_ADDR=http://localhost:8500
        
        echo "✅ Nomad and Consul are running!"
        echo ""
        echo "🌐 Access points:"
        echo "  - Nomad UI: http://localhost:4646/ui"
        echo "  - Consul UI: http://localhost:8500/ui"
        echo ""
        
        # Deploy ImageFlowCanvas services
        echo "🚀 Deploying ImageFlowCanvas services..."
        $0 deploy
        ;;
    
    "deploy")
        echo "📦 Deploying ImageFlowCanvas to Nomad..."
        
        # Check if Nomad and Consul are running
        if ! curl -f -s "http://localhost:4646" >/dev/null 2>&1; then
            echo "⚠️ Nomad is not running. Starting Nomad and Consul..."
            
            # Setup host volumes for Nomad
            setup_host_volumes
            
            # Start Consul in development mode
            echo "🏃 Starting Consul with configuration..."
            CONSUL_CONFIG="$NOMAD_DIR/consul.hcl"
            if [ -f "$CONSUL_CONFIG" ]; then
                consul agent -config-file="$CONSUL_CONFIG" &
            else
                echo "⚠️ Consul config not found, using dev mode"
                consul agent -dev -client=0.0.0.0 -bind=127.0.0.1 &
            fi
            CONSUL_PID=$!
            
            # Wait for Consul to be ready
            wait_for_service "Consul" "8500"
            
            # Start Nomad in development mode
            echo "🏃 Starting Nomad in development mode..."
            CPU_CORES=$(nproc)
            echo "  Detected ${CPU_CORES} CPU cores"
            
            # Create Nomad configuration and start with it
            echo "📝 Setting up Nomad configuration..."
            NOMAD_CONFIG=$(setup_nomad_config)
            if [ $? -ne 0 ]; then
                echo "❌ Failed to setup Nomad configuration"
                exit 1
            fi
            echo "✅ Nomad configuration generated at: $NOMAD_CONFIG"
            sudo nomad agent -config="$NOMAD_CONFIG" -bind=0.0.0.0 &
            NOMAD_PID=$!
            
            # Wait for Nomad to be ready  
            wait_for_service "Nomad" "4646"
            
            echo "✅ Nomad and Consul are now running!"
        else
            echo "✅ Nomad and Consul are already running!"
        fi
        
        # Set environment variables
        export NOMAD_ADDR=http://localhost:4646
        export CONSUL_HTTP_ADDR=http://localhost:8500
        
        # Build services first
        echo "🔨 Building Docker images..."
        cd "$BASE_DIR"
        ./scripts/build_services.sh
        
        # Deploy infrastructure services
        echo "🏗️ Deploying infrastructure services..."
        nomad job run -detach "$NOMAD_DIR/infrastructure.nomad"
        
        # Wait for infrastructure to be ready
        echo "⏳ Waiting for infrastructure services to be ready..."
        echo "  This may take several minutes as database and message queue services start up..."
        
        # Check deployment status periodically
        for i in {1..20}; do
            echo "  Checking deployment status... (attempt $i/20)"
            if nomad job status imageflow-infrastructure | grep -q "Status.*running"; then
                echo "✅ Infrastructure deployment completed!"
                break
            elif [ $i -eq 20 ]; then
                echo "⚠️ Infrastructure deployment is taking longer than expected."
                echo "   You can check the status with: nomad job status imageflow-infrastructure"
                echo "   Proceeding with next deployments..."
                break
            fi
            sleep 15
        done
        
        # Deploy gRPC services
        echo "🔧 Deploying gRPC services..."
        nomad job run -detach "$NOMAD_DIR/grpc-services.nomad"
        
        # Wait for gRPC services to be ready
        echo "⏳ Waiting for gRPC services to be ready..."
        for i in {1..12}; do
            echo "  Checking gRPC services status... (attempt $i/12)"
            if nomad job status imageflow-grpc-services | grep -q "Status.*running"; then
                echo "✅ gRPC services deployment completed!"
                break
            elif [ $i -eq 12 ]; then
                echo "⚠️ gRPC services deployment is taking longer than expected."
                echo "   Proceeding with application deployment..."
                break
            fi
            sleep 10
        done
        
        # Deploy application services
        echo "🌐 Deploying application services..."
        nomad job run -detach "$NOMAD_DIR/application.nomad"
        
        echo "✅ All services deployment initiated!"
        echo ""
        echo "🔍 To check deployment status:"
        echo "  nomad job status imageflow-infrastructure"
        echo "  nomad job status imageflow-grpc-services"
        echo "  nomad job status imageflow-application"
        echo ""
        echo "🌐 Access points (available once services are healthy):"
        echo "  - Frontend: http://localhost:3000"
        echo "  - Backend API: http://localhost:8000/docs"
        echo "  - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
        echo "  - gRPC Gateway: http://localhost:8080/health"
        echo "  - Nomad UI: http://localhost:4646/ui"
        echo "  - Consul UI: http://localhost:8500/ui"
        echo ""
        echo "💡 Use './scripts/setup-nomad-consul.sh status' to check current status"
        echo "💡 Use './scripts/setup-nomad-consul.sh health' to check service health"
        ;;
    
    "stop")
        echo "⏹️ Stopping ImageFlowCanvas services..."
        
        # Check if Nomad is running
        if ! curl -f -s "http://localhost:4646" >/dev/null 2>&1; then
            echo "❌ Nomad is not running. No services to stop."
            exit 1
        fi
        
        export NOMAD_ADDR=http://localhost:4646
        
        # Stop all jobs
        nomad job stop imageflow-application
        nomad job stop imageflow-grpc-services  
        nomad job stop imageflow-infrastructure
        
        echo "✅ All services stopped successfully!"
        ;;
    
    "status")
        echo "📊 ImageFlowCanvas service status:"
        
        # Check if Nomad is running
        if ! curl -f -s "http://localhost:4646" >/dev/null 2>&1; then
            echo "❌ Nomad is not running."
            echo "   Use './scripts/setup-nomad-consul.sh setup' to start Nomad and Consul"
            exit 1
        fi
        
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
        
        # Check if Nomad is running first
        if ! curl -f -s "http://localhost:4646" >/dev/null 2>&1; then
            echo "❌ Nomad cluster is not running."
            echo "   Use './scripts/setup-nomad-consul.sh setup' to start the cluster"
            exit 1
        fi
        
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
    
    "kill")
        echo "🔪 Killing Nomad and Consul processes..."
        cleanup_processes
        ;;
    
    *)
        echo "❓ Usage: $0 {setup|deploy|stop|status|logs|health|kill}"
        echo ""
        echo "Commands:"
        echo "  setup   - Install and setup Nomad/Consul environment"
        echo "  deploy  - Deploy ImageFlowCanvas services"
        echo "  stop    - Stop all services"
        echo "  status  - Show job status"
        echo "  logs    - Show service logs"
        echo "  health  - Check service health"
        echo "  kill    - Kill Nomad and Consul background processes"
        exit 1
        ;;
esac