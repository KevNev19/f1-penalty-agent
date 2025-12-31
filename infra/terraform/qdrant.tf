# Qdrant Cloud Cluster Configuration
# Creates a Qdrant Cloud cluster on GCP for the F1 Penalty Agent
#
# Prerequisites:
# - QDRANT_CLOUD_API_KEY environment variable set (from cloud.qdrant.io > API Keys)
# - QDRANT_ACCOUNT_ID environment variable set (from cloud.qdrant.io > Account Settings)

# Get available packages for the selected cloud provider and region
data "qdrant-cloud_booking_packages" "gcp" {
  cloud_provider = "gcp"
  cloud_region   = var.qdrant_region # Configurable region (default: Frankfurt)
}

# Select the free tier package (smallest available)
locals {
  # Find the free tier package (1 vCPU, 1GB RAM)
  free_tier_package = [
    for pkg in data.qdrant-cloud_booking_packages.gcp.packages : pkg
    if pkg.resource_configuration[0].ram == "1Gi"
  ]
}

# Create the Qdrant cluster
resource "qdrant-cloud_accounts_cluster" "f1_agent" {
  name           = "f1-penalty-agent"
  cloud_provider = data.qdrant-cloud_booking_packages.gcp.cloud_provider
  cloud_region   = data.qdrant-cloud_booking_packages.gcp.cloud_region

  configuration {
    number_of_nodes = 1

    database_configuration {
      service {
        jwt_rbac = true # Qdrant Cloud requires JWT RBAC to be enabled
      }
    }

    # Explicitly set defaults to avoid drift
    gpu_type           = "CLUSTER_CONFIGURATION_GPU_TYPE_UNSPECIFIED"
    rebalance_strategy = "CLUSTER_CONFIGURATION_REBALANCE_STRATEGY_BY_COUNT_AND_SIZE"
    restart_policy     = "CLUSTER_CONFIGURATION_RESTART_POLICY_UNSPECIFIED"
    service_type       = "CLUSTER_SERVICE_TYPE_CLUSTER_IP"

    node_configuration {
      package_id = local.free_tier_package[0].id
    }
  }
}

# Create an API key for the cluster
resource "qdrant-cloud_accounts_database_api_key_v2" "f1_agent_key" {
  cluster_id = qdrant-cloud_accounts_cluster.f1_agent.id
  name       = "f1-agent-api-key"
}

# Output the cluster URL
output "qdrant_cluster_url" {
  description = "Qdrant Cloud cluster URL"
  value       = qdrant-cloud_accounts_cluster.f1_agent.url
}

# Output the API key (sensitive)
output "qdrant_api_key" {
  description = "Qdrant Cloud API key for the cluster"
  value       = qdrant-cloud_accounts_database_api_key_v2.f1_agent_key.key
  sensitive   = true
}

# Output the cluster ID
output "qdrant_cluster_id" {
  description = "Qdrant Cloud cluster ID"
  value       = qdrant-cloud_accounts_cluster.f1_agent.id
}
