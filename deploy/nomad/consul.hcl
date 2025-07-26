# Consul development configuration for ImageFlowCanvas
datacenter = "dc1"
data_dir = "/tmp/consul"

# Development mode settings
server = true
bootstrap_expect = 1

# Network configuration
bind_addr = "127.0.0.1"
client_addr = "0.0.0.0"

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

# Ports configuration
ports {
  grpc = 8502
  grpc_tls = 8503
}
