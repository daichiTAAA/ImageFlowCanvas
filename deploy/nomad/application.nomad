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
        network_mode = "host"
        dns_servers = ["127.0.0.1:8600", "8.8.8.8"]
      }

      env {
        DEPLOYMENT_ENV          = "nomad"
        NOMAD_IP               = "192.168.5.15"
        DATABASE_URL            = "postgresql+asyncpg://imageflow:imageflow123@192.168.5.15:5432/imageflow"
        # Fallback database URL in case Consul DNS fails
        DATABASE_URL_FALLBACK   = "postgresql+asyncpg://imageflow:imageflow123@localhost:5432/imageflow"
        MINIO_ENDPOINT          = "192.168.5.15:9000"
        MINIO_ACCESS_KEY        = "minioadmin"
        MINIO_SECRET_KEY        = "minioadmin"
        KAFKA_BOOTSTRAP_SERVERS = "192.168.5.15:29092"
        SECRET_KEY              = "your-secret-key-change-in-production"
        TRITON_URL              = "192.168.5.15:8011"
        GRPC_GATEWAY_URL        = "192.168.5.15:8080"
        # Environment indicator for Nomad
        NOMAD_DEPLOYMENT        = "true"
        # Debug settings
        PYTHONUNBUFFERED        = "1"
        LOG_LEVEL               = "DEBUG"
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
        network_mode = "host"
        dns_servers = ["127.0.0.1:8600", "8.8.8.8"]
      }

      env {
        DEPLOYMENT_ENV    = "nomad"
        NOMAD_IP         = "192.168.5.15"
        REACT_APP_API_URL = "http://192.168.5.15:8000"
        REACT_APP_WS_URL  = "ws://192.168.5.15:8000"
        BACKEND_HOST      = "192.168.5.15"
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