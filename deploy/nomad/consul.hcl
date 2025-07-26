# Consul development configuration for ImageFlowCanvas
datacenter = "dc1"
data_dir = "/tmp/consul"

# Development mode settings
server = true
bootstrap_expect = 1

# Network configuration
bind_addr = "192.168.5.15"
advertise_addr = "192.168.5.15"
client_addr = "0.0.0.0"

# Recursors for external DNS queries
recursors = ["8.8.8.8", "1.1.1.1"]

# UI configuration
ui_config {
  enabled = true
}

# Log configuration
log_level = "INFO"
log_file = "/tmp/consul.log"

# Performance settings
performance {
  raft_multiplier = 1
}

# Connect configuration for service mesh
connect {
  enabled = true
}

# DNS configuration
dns_config {
  enable_truncate = true
  only_passing = true
  allow_stale = true
  max_stale = "87600h"
  node_ttl = "30s"
  service_ttl = {
    "*" = "30s"
  }
  enable_additional_node_meta_txt = false
}

# Ports configuration
ports {
  grpc = 8502
  grpc_tls = 8503
  dns = 8600
}

# Additional DNS bind addresses for better accessibility
addresses {
  dns = "0.0.0.0"
  http = "0.0.0.0"
  https = "0.0.0.0"
  grpc = "0.0.0.0"
}
