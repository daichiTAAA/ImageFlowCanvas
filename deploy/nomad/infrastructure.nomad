job "imageflow-infrastructure" {
  datacenters = ["dc1"]
  type        = "service"

  group "database" {
    count = 1

    network {
      port "postgres" {
        static = 5432
      }
    }

    volume "postgres_data" {
      type      = "host"
      read_only = false
      source    = "postgres_data"
    }

    task "postgres" {
      driver = "docker"

      config {
        image = "postgres:17-alpine"
        ports = ["postgres"]
      }

      volume_mount {
        volume      = "postgres_data"
        destination = "/var/lib/postgresql/data"
        read_only   = false
      }

      env {
        POSTGRES_DB       = "imageflow"
        POSTGRES_USER     = "imageflow"
        POSTGRES_PASSWORD = "imageflow123"
        PGDATA           = "/var/lib/postgresql/data/pgdata"
      }

      resources {
        cpu    = 500
        memory = 512
      }

      service {
        name = "postgres"
        port = "postgres"
        
        check {
          type     = "script"
          name     = "postgres-health"
          command  = "pg_isready"
          args     = ["-U", "imageflow", "-h", "localhost", "-p", "5432"]
          interval = "10s"
          timeout  = "5s"
        }
      }
    }
  }

  group "message-queue" {
    count = 1

    network {
      port "zookeeper" {
        static = 2181
      }
      port "kafka" {
        static = 9092
      }
      port "kafka_internal" {
        static = 29092
      }
    }

    task "zookeeper" {
      driver = "docker"

      config {
        image = "confluentinc/cp-zookeeper:7.4.0"
        ports = ["zookeeper"]
      }

      env {
        ZOOKEEPER_CLIENT_PORT = "2181"
        ZOOKEEPER_TICK_TIME   = "2000"
      }

      resources {
        cpu    = 200
        memory = 256
      }

      service {
        name = "zookeeper"
        port = "zookeeper"
        
        check {
          type     = "tcp"
          interval = "10s"
          timeout  = "3s"
        }
      }
    }

    task "kafka" {
      driver = "docker"

      config {
        image = "confluentinc/cp-kafka:7.4.0"
        ports = ["kafka", "kafka_internal"]
      }

      env {
        KAFKA_BROKER_ID                         = "1"
        KAFKA_ZOOKEEPER_CONNECT                 = "zookeeper.service.consul:2181"
        KAFKA_LISTENER_SECURITY_PROTOCOL_MAP    = "PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT"
        KAFKA_ADVERTISED_LISTENERS              = "PLAINTEXT://kafka.service.consul:29092,PLAINTEXT_HOST://localhost:9092"
        KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR  = "1"
        KAFKA_TRANSACTION_STATE_LOG_MIN_ISR     = "1"
        KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR = "1"
      }

      resources {
        cpu    = 500
        memory = 1024
      }

      service {
        name = "kafka"
        port = "kafka_internal"
        
        check {
          type     = "tcp"
          interval = "10s"
          timeout  = "3s"
        }
      }
    }
  }

  group "object-storage" {
    count = 1

    network {
      port "minio_api" {
        static = 9000
      }
      port "minio_console" {
        static = 9001
      }
    }

    volume "minio_data" {
      type      = "host"
      read_only = false
      source    = "minio_data"
    }

    task "minio" {
      driver = "docker"

      config {
        image = "minio/minio:RELEASE.2023-09-04T19-57-37Z"
        ports = ["minio_api", "minio_console"]
        command = "minio"
        args = ["server", "/data", "--console-address", ":9001"]
      }

      volume_mount {
        volume      = "minio_data"
        destination = "/data"
        read_only   = false
      }

      env {
        MINIO_ROOT_USER     = "minioadmin"
        MINIO_ROOT_PASSWORD = "minioadmin"
      }

      resources {
        cpu    = 300
        memory = 512
      }

      service {
        name = "minio-api"
        port = "minio_api"
        
        check {
          type     = "http"
          path     = "/minio/health/live"
          interval = "30s"
          timeout  = "3s"
        }
      }

      service {
        name = "minio-console"
        port = "minio_console"
        
        check {
          type     = "tcp"
          interval = "30s"
          timeout  = "3s"
        }
      }
    }
  }

  group "ai-inference" {
    count = 1

    network {
      port "triton_http" {
        static = 8001
      }
      port "triton_grpc" {
        static = 8011
      }
      port "triton_metrics" {
        static = 8002
      }
    }

    task "triton" {
      driver = "docker"

      config {
        image = "nvcr.io/nvidia/tritonserver:23.10-py3"
        ports = ["triton_http", "triton_grpc", "triton_metrics"]
        command = "tritonserver"
        args = [
          "--model-repository=/models",
          "--strict-model-config=false",
          "--log-verbose=1"
        ]
      }

      resources {
        cpu    = 1000
        memory = 2048
      }

      service {
        name = "triton"
        port = "triton_http"
        
        check {
          type     = "http"
          path     = "/v2/health/ready"
          interval = "30s"
          timeout  = "10s"
        }
      }
    }
  }
}