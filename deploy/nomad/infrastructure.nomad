job "imageflow-infrastructure" {
  datacenters = ["dc1"]
  type        = "service"

  update {
    max_parallel     = 1
    min_healthy_time = "10s"
    healthy_deadline = "3m"
    auto_revert      = false
    canary           = 0
  }

  group "database" {
    count = 1

    update {
      max_parallel     = 1
      min_healthy_time = "10s" 
      healthy_deadline = "3m"
      auto_revert      = false
      canary           = 0
    }

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
        cpu    = 100
        memory = 256
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

    update {
      max_parallel     = 1
      min_healthy_time = "10s"
      healthy_deadline = "3m"
      auto_revert      = false
      canary           = 0
    }

    network {
      port "kafka" {
        static = 9092
      }
      port "kafka_internal" {
        static = 29092
      }
      port "kafka_controller" {
        static = 29093
      }
    }

    volume "kafka_data" {
      type      = "host"
      read_only = false
      source    = "kafka_data"
    }

    task "kafka" {
      driver = "docker"

      config {
        image = "confluentinc/cp-kafka:7.6.0"
        ports = ["kafka", "kafka_internal", "kafka_controller"]
        force_pull = false
        command = "bash"
        args = [
          "-c",
          "if [ ! -f /var/lib/kafka/data/meta.properties ]; then /bin/kafka-storage format -t $CLUSTER_ID -c /etc/kafka/kraft/server.properties; fi && /etc/confluent/docker/run"
        ]
      }

      volume_mount {
        volume      = "kafka_data"
        destination = "/var/lib/kafka"
        read_only   = false
      }

      env {
        CLUSTER_ID                              = "4L6g3nShT-eMCtK--X86sw"
        KAFKA_NODE_ID                           = "1"
        KAFKA_PROCESS_ROLES                     = "broker,controller"
        KAFKA_CONTROLLER_QUORUM_VOTERS          = "1@localhost:29093"
        KAFKA_LISTENERS                         = "PLAINTEXT://localhost:29092,CONTROLLER://localhost:29093,PLAINTEXT_HOST://0.0.0.0:9092"
        KAFKA_INTER_BROKER_LISTENER_NAME        = "PLAINTEXT"
        KAFKA_CONTROLLER_LISTENER_NAMES         = "CONTROLLER"
        KAFKA_LISTENER_SECURITY_PROTOCOL_MAP    = "PLAINTEXT:PLAINTEXT,CONTROLLER:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT"
        KAFKA_ADVERTISED_LISTENERS              = "PLAINTEXT://localhost:29092,PLAINTEXT_HOST://localhost:9092"
        KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR  = "1"
        KAFKA_GROUP_INITIAL_REBALANCE_DELAY_MS  = "0"
        KAFKA_TRANSACTION_STATE_LOG_MIN_ISR     = "1"
        KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR = "1"
        KAFKA_LOG_DIRS                          = "/var/lib/kafka/data"
      }

      resources {
        cpu    = 300
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

    update {
      max_parallel     = 1
      min_healthy_time = "10s"
      healthy_deadline = "3m"
      auto_revert      = false
      canary           = 0
    }

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
        image = "minio/minio:RELEASE.2025-07-23T15-54-02Z"
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
        cpu    = 150
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

    update {
      max_parallel     = 1
      min_healthy_time = "10s"
      healthy_deadline = "3m"
      auto_revert      = false
      canary           = 0
    }

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

    volume "models_data" {
      type      = "host"
      read_only = true
      source    = "models_data"
    }

    task "triton" {
      driver = "docker"

      config {
        image = "nvcr.io/nvidia/tritonserver:24.07-py3"
        ports = ["triton_http", "triton_grpc", "triton_metrics"]
        command = "tritonserver"
        args = [
          "--model-repository=/models",
          "--strict-model-config=false",
          "--log-verbose=1"
        ]
        # Increase pull timeout for large images
        image_pull_timeout = "20m"
      }

      volume_mount {
        volume      = "models_data"
        destination = "/models"
        read_only   = true
      }

      resources {
        cpu    = 400
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