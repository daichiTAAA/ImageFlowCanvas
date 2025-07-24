job "imageflow-application" {
  datacenters = ["dc1"]
  type        = "service"

  group "backend" {
    count = 1

    network {
      port "http" {
        static = 8000
      }
    }

    task "backend" {
      driver = "docker"

      config {
        image = "imageflow/backend:latest"
        ports = ["http"]
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
        cpu    = 500
        memory = 1024
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

    network {
      port "http" {
        static = 3000
      }
    }

    task "frontend" {
      driver = "docker"

      config {
        image = "imageflow/frontend:latest"
        ports = ["http"]
      }

      env {
        REACT_APP_API_URL = "http://backend.service.consul:8000"
        REACT_APP_WS_URL  = "ws://backend.service.consul:8000"
      }

      resources {
        cpu    = 300
        memory = 512
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