#!/bin/bash

# ImageFlowCanvas Multi-Environment Status Checker
#
# Usage:
#   ./scripts/status.sh                    # Check all environments
#   ./scripts/status.sh compose            # Check Docker Compose only
#   ./scripts/status.sh k3s                # Check K3s only
#   ./scripts/status.sh nomad              # Check Nomad only

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENVIRONMENT=${1:-"all"}

echo "🔍 ImageFlowCanvas Multi-Environment Status"
echo "Base Directory: $BASE_DIR"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is open
check_port() {
    local port=$1
    local service=$2
    if nc -z localhost "$port" 2>/dev/null; then
        echo "✅ $service (port $port): Running"
        return 0
    else
        echo "❌ $service (port $port): Down"
        return 1
    fi
}

# Function to check Docker Compose status
check_compose() {
    echo "🐳 Docker Compose Status"
    echo "========================"
    
    if ! command_exists docker; then
        echo "❌ Docker not installed"
        return 1
    fi
    
    cd "$BASE_DIR/deploy/compose"
    
    if docker compose ps --format table | grep -q "Up"; then
        echo "📊 Running services:"
        docker compose ps --format table
        echo ""
        echo "🔍 Health checks:"
        check_port 3000 "Web UI"
        check_port 8000 "Backend API"
        check_port 9001 "MinIO Console"
        check_port 8080 "gRPC Gateway"
        check_port 5432 "PostgreSQL"
    else
        echo "❌ No services running"
        echo ""
        echo "💡 To start services: ./scripts/run-compose.sh build"
    fi
    
    echo ""
}

# Function to check K3s status  
check_k3s() {
    echo "⚙️ K3s Status"
    echo "=============="
    
    if ! command_exists kubectl; then
        echo "❌ kubectl not installed"
        return 1
    fi
    
    if ! kubectl get nodes &>/dev/null; then
        echo "❌ K3s cluster not accessible"
        echo ""
        echo "💡 To setup K3s: sudo ./scripts/setup-k3s.sh"
        return 1
    fi
    
    echo "📊 Cluster nodes:"
    kubectl get nodes
    
    echo ""
    echo "📊 Running pods:"
    kubectl get pods --all-namespaces | grep -E "(Running|Pending|Error|CrashLoopBackOff)" || echo "No pods found"
    
    echo ""
    echo "🔍 Service health:"
    if kubectl get svc | grep -q web-service; then
        echo "✅ Services deployed"
        
        # Check if port-forward is running
        if pgrep -f "kubectl.*port-forward" >/dev/null; then
            echo "✅ Port forwarding active"
            check_port 3000 "Web UI (port-forward)"
            check_port 8000 "Backend API (port-forward)"
            check_port 9001 "MinIO Console (port-forward)"
        else
            echo "❌ Port forwarding not active"
            echo ""
            echo "💡 To start port forwarding: ./scripts/port-forward.sh"
        fi
    else
        echo "❌ Services not deployed"
        echo ""
        echo "💡 To deploy: sudo ./scripts/setup-k3s.sh"
    fi
    
    echo ""
}

# Function to check Nomad status
check_nomad() {
    echo "🏗️ Nomad Status"
    echo "==============="
    
    if ! command_exists nomad; then
        echo "❌ Nomad not installed"
        echo ""
        echo "💡 To setup Nomad: ./scripts/setup-nomad-consul.sh"
        return 1
    fi
    
    export NOMAD_ADDR=http://localhost:4646
    
    if ! nomad server members &>/dev/null; then
        echo "❌ Nomad server not accessible"
        echo ""
        echo "💡 To start Nomad: ./scripts/setup-nomad-consul.sh"
        return 1
    fi
    
    echo "📊 Nomad server status:"
    nomad server members
    
    echo ""
    echo "📊 Running jobs:"
    nomad job status || echo "No jobs found"
    
    echo ""
    echo "🔍 Service health:"
    check_port 4646 "Nomad UI"
    check_port 8500 "Consul UI" 
    check_port 3000 "Web UI"
    check_port 8000 "Backend API"
    check_port 9001 "MinIO Console"
    
    echo ""
}

# Main execution
case "$ENVIRONMENT" in
    "compose")
        check_compose
        ;;
    "k3s")
        check_k3s
        ;;
    "nomad")
        check_nomad
        ;;
    "all")
        check_compose
        check_k3s
        check_nomad
        ;;
    *)
        echo "❓ Usage: $0 {all|compose|k3s|nomad}"
        echo ""
        echo "Environments:"
        echo "  all     - Check all environments"
        echo "  compose - Check Docker Compose"
        echo "  k3s     - Check K3s cluster"
        echo "  nomad   - Check Nomad cluster"
        exit 1
        ;;
esac

echo "🎯 Quick Access Links"
echo "==================="
echo "Web UI:        http://localhost:3000"
echo "Backend API:   http://localhost:8000/docs"
echo "MinIO Console: http://localhost:9001 (minioadmin/minioadmin)"
echo "Nomad UI:      http://localhost:4646"
echo "Consul UI:     http://localhost:8500"