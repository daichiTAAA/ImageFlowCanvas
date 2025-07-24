job "imageflow-grpc-services" {
  datacenters = ["dc1"]
  type        = "service"

  group "resize-service" {
    count = 1

    network {
      port "grpc" {
        static = 9090
      }
    }

    task "resize-grpc" {
      driver = "docker"

      config {
        image = "imageflow/resize-grpc:latest"
        ports = ["grpc"]
      }

      env {
        MINIO_ENDPOINT   = "minio-api.service.consul:9000"
        MINIO_ACCESS_KEY = "minioadmin"
        MINIO_SECRET_KEY = "minioadmin"
        GRPC_PORT        = "9090"
        GRPC_MAX_WORKERS = "25"
      }

      resources {
        cpu    = 300
        memory = 768
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
        image = "imageflow/ai-detection-grpc:latest"
        ports = ["grpc"]
      }

      env {
        MINIO_ENDPOINT    = "minio-api.service.consul:9000"
        MINIO_ACCESS_KEY  = "minioadmin"
        MINIO_SECRET_KEY  = "minioadmin"
        TRITON_URL        = "triton.service.consul:8001"
        GRPC_PORT         = "9090"
        GRPC_MAX_WORKERS  = "25"
      }

      resources {
        cpu    = 500
        memory = 1024
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
        static = 9092
      }
    }

    task "filter-grpc" {
      driver = "docker"

      config {
        image = "imageflow/filter-grpc:latest"
        ports = ["grpc"]
      }

      env {
        MINIO_ENDPOINT   = "minio-api.service.consul:9000"
        MINIO_ACCESS_KEY = "minioadmin"
        MINIO_SECRET_KEY = "minioadmin"
        GRPC_PORT        = "9090"
        GRPC_MAX_WORKERS = "25"
      }

      resources {
        cpu    = 300
        memory = 768
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
        static = 9093
      }
    }

    task "camera-stream-grpc" {
      driver = "docker"

      config {
        image = "imageflow/camera-stream-grpc:latest"
        ports = ["grpc"]
      }

      env {
        MINIO_ENDPOINT   = "minio-api.service.consul:9000"
        MINIO_ACCESS_KEY = "minioadmin"
        MINIO_SECRET_KEY = "minioadmin"
        GRPC_PORT        = "9090"
        GRPC_MAX_WORKERS = "25"
      }

      resources {
        cpu    = 400
        memory = 1024
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
        image = "imageflow/grpc-gateway:latest"
        ports = ["http"]
      }

      env {
        RESIZE_GRPC_URL        = "resize-grpc.service.consul:9090"
        AI_DETECTION_GRPC_URL  = "ai-detection-grpc.service.consul:9091"
        FILTER_GRPC_URL        = "filter-grpc.service.consul:9092"
        CAMERA_STREAM_GRPC_URL = "camera-stream-grpc.service.consul:9093"
        GATEWAY_PORT           = "8080"
      }

      resources {
        cpu    = 200
        memory = 512
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