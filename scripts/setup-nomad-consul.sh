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
#   ./scripts/setup-nomad-consul.sh kill           # Kill Nomad and Consul background processes + stop containers
#   ./scripts/setup-nomad-consul.sh cleanup        # Complete cleanup including Docker resources

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

# Function to setup Consul DNS forwarding
setup_consul_dns() {
    echo "🔧 Setting up Consul DNS forwarding..."
    
    # Check if Consul DNS is already configured
    local consul_config="/etc/systemd/resolved.conf.d/consul.conf"
    local needs_config=false
    
    if [ ! -f "$consul_config" ]; then
        echo "  Consul DNS configuration not found, creating..."
        needs_config=true
    else
        # Check if existing configuration is correct
        if ! grep -q "DNS=127.0.0.1:8600" "$consul_config" || ! grep -q "Domains=~consul" "$consul_config"; then
            echo "  Existing Consul DNS configuration is incomplete, updating..."
            needs_config=true
        else
            echo "  ✅ Consul DNS configuration already exists and is correct"
            
            # Verify if systemd-resolved is actually using the configuration
            if resolvectl status | grep -q "DNS Domain: ~consul" && resolvectl status | grep -q "DNS Servers: 127.0.0.1:8600"; then
                echo "  ✅ systemd-resolved is already configured for Consul DNS"
                return 0
            else
                echo "  Configuration file exists but systemd-resolved needs restart"
                needs_config=true
            fi
        fi
    fi
    
    if [ "$needs_config" = true ]; then
        echo "  Configuring systemd-resolved to forward .consul queries..."
        
        # Configure systemd-resolved to forward .consul queries to Consul
        sudo mkdir -p /etc/systemd/resolved.conf.d
        sudo tee "$consul_config" > /dev/null << EOF
[Resolve]
DNS=127.0.0.1:8600
Domains=~consul
FallbackDNS=8.8.8.8 1.1.1.1
EOF
        
        echo "  Restarting systemd-resolved..."
        sudo systemctl restart systemd-resolved
        
        # Wait for service to be ready
        sleep 3
        
        echo "✅ Consul DNS configured via systemd-resolved"
    fi
}

# Function to test Consul DNS resolution
test_consul_dns() {
    echo "🧪 Testing Consul DNS resolution..."
    
    # Wait for Consul to be ready
    local max_attempts=10
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "http://localhost:8500" >/dev/null 2>&1; then
            break
        fi
        echo "  Waiting for Consul to be ready... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        echo "  ⚠️ Consul is not ready, skipping DNS tests"
        return 1
    fi
    
    # Test DNS resolution
    echo "  Testing direct Consul DNS query..."
    if dig @127.0.0.1 -p 8600 consul.service.consul +short >/dev/null 2>&1; then
        echo "  ✅ Direct Consul DNS query successful"
    else
        echo "  ❌ Direct Consul DNS query failed"
    fi
    
    # Test systemd-resolved configuration
    echo "  Testing systemd-resolved configuration..."
    local resolved_status=$(resolvectl status 2>/dev/null)
    if echo "$resolved_status" | grep -q "DNS Domain: ~consul"; then
        echo "  ✅ systemd-resolved is configured for Consul DNS"
        
        # Check if DNS servers include Consul
        if echo "$resolved_status" | grep -q "DNS Servers: 127.0.0.1:8600"; then
            echo "  ✅ systemd-resolved is using Consul DNS server"
        else
            echo "  ⚠️ systemd-resolved configured but not using Consul DNS server"
        fi
    else
        echo "  ❌ systemd-resolved configuration issue"
        echo "  Current DNS configuration:"
        echo "$resolved_status" | head -10 | sed 's/^/    /'
        return 1
    fi
    
    # Test .consul domain resolution
    echo "  Testing .consul domain resolution..."
    if resolvectl query consul.service.consul >/dev/null 2>&1; then
        echo "  ✅ Consul DNS resolution via systemd-resolved successful"
    else
        echo "  ❌ Consul DNS resolution via systemd-resolved failed"
    fi
    
    # Test external DNS resolution
    echo "  Testing external DNS resolution..."
    if nslookup google.com >/dev/null 2>&1; then
        echo "  ✅ External DNS resolution working"
    else
        echo "  ⚠️ External DNS resolution failed"
    fi
    
    return 0
}

# Function to cleanup background processes
cleanup_processes() {
    echo "🧹 Cleaning up background processes..."
    
    # First try to stop Nomad jobs gracefully if Nomad is running
    if curl -f -s "http://localhost:4646" >/dev/null 2>&1; then
        echo "  Stopping Nomad jobs gracefully..."
        export NOMAD_ADDR=http://localhost:4646
        nomad job stop imageflow-application || true
        nomad job stop imageflow-grpc-services || true  
        nomad job stop imageflow-infrastructure || true
        sleep 3
    fi
    
    # Kill Consul and Nomad processes
    echo "  Stopping Nomad and Consul processes..."
    pkill -f "consul agent" || true
    pkill -f "nomad agent" || true
    
    # Wait a bit for graceful shutdown
    sleep 2
    
    # Force kill if still running
    pkill -9 -f "consul agent" || true
    pkill -9 -f "nomad agent" || true
    
    # Stop any remaining Docker containers managed by Nomad
    echo "  Stopping any remaining Docker containers..."
    RUNNING_CONTAINERS=$(docker ps -q)
    if [ ! -z "$RUNNING_CONTAINERS" ]; then
        echo "  Found running containers, stopping them..."
        docker stop $RUNNING_CONTAINERS || true
    else
        echo "  No running containers found"
    fi
    
    echo "✅ Background processes and containers cleaned up"
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
        
        # Setup Consul DNS forwarding (only if needed)
        setup_consul_dns
        
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
        
        # Test Consul DNS resolution
        test_consul_dns
        
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
            
            # Setup Consul DNS forwarding (only if needed)
            setup_consul_dns
            
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
    
    "cleanup")
        echo "🧽 Complete cleanup of all resources..."
        cleanup_processes
        
        # Also remove stopped containers and unused images
        echo "🗑️  Cleaning up Docker resources..."
        docker container prune -f || true
        docker image prune -f || true
        docker volume prune -f || true
        docker network prune -f || true
        
        echo "✅ Complete cleanup finished!"
        ;;
    
    *)
        echo "❓ Usage: $0 {setup|deploy|stop|status|logs|health|kill|cleanup}"
        echo ""
        echo "Commands:"
        echo "  setup   - Install and setup Nomad/Consul environment"
        echo "  deploy  - Deploy ImageFlowCanvas services"
        echo "  stop    - Stop all services"
        echo "  status  - Show job status"
        echo "  logs    - Show service logs"
        echo "  health  - Check service health"
        echo "  kill    - Kill Nomad and Consul background processes"
        echo "  cleanup - Complete cleanup including Docker resources"
        exit 1
        ;;
esac