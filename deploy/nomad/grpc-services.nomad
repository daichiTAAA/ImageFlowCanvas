job "imageflow-grpc-services" {
  datacenters = ["dc1"]
  type        = "service"

  update {
    max_parallel     = 1
    min_healthy_time = "10s"
    healthy_deadline = "5m"
    auto_revert      = false
    canary           = 0
  }

  group "resize-service" {
    count = 1

    update {
      max_parallel     = 1
      min_healthy_time = "10s"
      healthy_deadline = "5m"
      auto_revert      = false
      canary           = 0
    }

    network {
      port "grpc" {
        static = 9090
      }
    }

    task "resize-grpc" {
      driver = "docker"

      config {
        image = "imageflow/resize-grpc:local"
        ports = ["grpc"]
        force_pull = false
        network_mode = "host"
        dns_servers = ["127.0.0.1:8600", "8.8.8.8"]
      }

      env {
        DEPLOYMENT_ENV   = "nomad"
        NOMAD_IP         = "192.168.5.15"
        MINIO_ENDPOINT   = "192.168.5.15:9000"
        MINIO_ACCESS_KEY = "minioadmin"
        MINIO_SECRET_KEY = "minioadmin"
        GRPC_PORT        = "9090"
        GRPC_MAX_WORKERS = "25"
      }

      resources {
        cpu    = 150
        memory = 384
      }

      service {
        name = "resize-grpc"
        port = "grpc"
        
        check {
          type     = "tcp"
          interval = "30s"
          timeout  = "10s"
        }
      }
    }
  }

  group "ai-detection-service" {
    count = 1

    network {
      port "grpc" {
        static = 9091
      }
    }

    task "ai-detection-grpc" {
      driver = "docker"

      config {
        image = "imageflow/ai-detection-grpc:local"
        ports = ["grpc"]
        force_pull = false
        image_pull_timeout = "10m"
        network_mode = "host"
        dns_servers = ["127.0.0.1:8600", "8.8.8.8"]
      }

      env {
        DEPLOYMENT_ENV   = "nomad"
        NOMAD_IP         = "192.168.5.15"
        MINIO_ENDPOINT   = "192.168.5.15:9000"
        MINIO_ACCESS_KEY  = "minioadmin"
        MINIO_SECRET_KEY  = "minioadmin"
        TRITON_URL        = "192.168.5.15:8011"
        GRPC_PORT         = "9091"
        GRPC_MAX_WORKERS  = "25"
      }

      resources {
        cpu    = 250
        memory = 512
      }

      service {
        name = "ai-detection-grpc"
        port = "grpc"
        
        check {
          type     = "tcp"
          interval = "30s"
          timeout  = "10s"
        }
      }
    }
  }

  group "filter-service" {
    count = 1

    network {
      port "grpc" {
        static = 9093
      }
    }

    task "filter-grpc" {
      driver = "docker"

      config {
        image = "imageflow/filter-grpc:local"
        ports = ["grpc"]
        force_pull = false
        network_mode = "host"
        dns_servers = ["127.0.0.1:8600", "8.8.8.8"]
      }

      env {
        DEPLOYMENT_ENV   = "nomad"
        NOMAD_IP         = "192.168.5.15"
        MINIO_ENDPOINT   = "192.168.5.15:9000"
        MINIO_ACCESS_KEY = "minioadmin"
        MINIO_SECRET_KEY = "minioadmin"
        GRPC_PORT        = "9093"
        GRPC_MAX_WORKERS = "25"
      }

      resources {
        cpu    = 150
        memory = 384
      }

      service {
        name = "filter-grpc"
        port = "grpc"
        
        check {
          type     = "tcp"
          interval = "30s"
          timeout  = "10s"
        }
      }
    }
  }

  group "camera-stream-service" {
    count = 1

    network {
      port "grpc" {
        static = 9094
      }
    }

    task "camera-stream-grpc" {
      driver = "docker"

      config {
        image = "imageflow/camera-stream-grpc:local"
        ports = ["grpc"]
        force_pull = false
        network_mode = "host"
        dns_servers = ["127.0.0.1:8600", "8.8.8.8"]
      }

      env {
        DEPLOYMENT_ENV   = "nomad"
        NOMAD_IP         = "192.168.5.15"
        MINIO_ENDPOINT   = "192.168.5.15:9000"
        MINIO_ACCESS_KEY = "minioadmin"
        MINIO_SECRET_KEY = "minioadmin"
        GRPC_PORT        = "9094"
        GRPC_MAX_WORKERS = "25"
      }

      resources {
        cpu    = 200
        memory = 512
      }

      service {
        name = "camera-stream-grpc"
        port = "grpc"
        
        check {
          type     = "tcp"
          interval = "30s"
          timeout  = "10s"
        }
      }
    }
  }

  group "grpc-gateway" {
    count = 1

    network {
      port "http" {
        static = 8080
      }
    }

    task "grpc-gateway" {
      driver = "docker"

      config {
        image = "imageflow/grpc-gateway:local"
        ports = ["http"]
        force_pull = false
        network_mode = "host"
        dns_servers = ["127.0.0.1:8600", "8.8.8.8"]
      }

      env {
        DEPLOYMENT_ENV         = "nomad"
        NOMAD_IP              = "192.168.5.15"
        RESIZE_GRPC_URL        = "192.168.5.15:9090"
        AI_DETECTION_GRPC_URL  = "192.168.5.15:9091"
        FILTER_GRPC_URL        = "192.168.5.15:9093"
        CAMERA_STREAM_GRPC_URL = "192.168.5.15:9094"
        GATEWAY_PORT           = "8080"
      }

      resources {
        cpu    = 100
        memory = 256
      }

      service {
        name = "grpc-gateway"
        port = "http"
        
        check {
          type     = "http"
          path     = "/health"
          interval = "30s"
          timeout  = "10s"
        }
      }
    }
  }
}