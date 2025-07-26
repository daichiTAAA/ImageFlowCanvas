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
    path      = "/home/noda.linux/ImageFlowCanvas/models"
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
