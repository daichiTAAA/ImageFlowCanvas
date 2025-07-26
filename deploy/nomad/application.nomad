job "imageflow-application" {
  datacenters = ["dc1"]
  type        = "service"

  update {
    max_parallel     = 1
    min_healthy_time = "10s"
    healthy_deadline = "5m"
    auto_revert      = false
    canary           = 0
  }

  group "backend" {
    count = 1

    update {
      max_parallel     = 1
      min_healthy_time = "10s"
      healthy_deadline = "5m"
      auto_revert      = false
      canary           = 0
    }

    network {
      port "http" {
        static = 8000
      }
    }

    task "backend" {
      driver = "docker"

      config {
        image = "imageflow/backend:local"
        ports = ["http"]
        force_pull = false
        dns_servers = ["172.17.0.1", "8.8.8.8"]
        dns_search_domains = ["service.consul"]
      }

      env {
        DATABASE_URL            = "postgresql+asyncpg://imageflow:imageflow123@postgres.service.consul:5432/imageflow"
        MINIO_ENDPOINT          = "minio-api.service.consul:9000"
        MINIO_ACCESS_KEY        = "minioadmin"
        MINIO_SECRET_KEY        = "minioadmin"
        KAFKA_BOOTSTRAP_SERVERS = "kafka.service.consul:29092"
        SECRET_KEY              = "your-secret-key-change-in-production"
        TRITON_URL              = "triton.service.consul:8001"
        GRPC_GATEWAY_URL        = "grpc-gateway.service.consul:8080"
      }

      resources {
        cpu    = 200
        memory = 512
      }

      service {
        name = "backend"
        port = "http"
        
        check {
          type     = "http"
          path     = "/v1/health"
          interval = "30s"
          timeout  = "10s"
        }
      }
    }
  }

  group "frontend" {
    count = 1

    update {
      max_parallel     = 1
      min_healthy_time = "10s"
      healthy_deadline = "5m"
      auto_revert      = false
      canary           = 0
    }

    network {
      port "http" {
        static = 3000
      }
    }

    task "frontend" {
      driver = "docker"

      config {
        image = "imageflow/frontend:local"
        ports = ["http"]
        force_pull = false
        dns_servers = ["172.17.0.1", "8.8.8.8"]
        dns_search_domains = ["service.consul"]
      }

      env {
        REACT_APP_API_URL = "http://backend.service.consul:8000"
        REACT_APP_WS_URL  = "ws://backend.service.consul:8000"
        BACKEND_HOST      = "backend.service.consul"
        BACKEND_PORT      = "8000"
        NGINX_RESOLVER    = "resolver 172.17.0.1 8.8.8.8 valid=30s;"
      }

      resources {
        cpu    = 200
        memory = 256
      }

      service {
        name = "frontend"
        port = "http"
        
        check {
          type     = "tcp"
          interval = "30s"
          timeout  = "10s"
        }
      }
    }
  }
}