variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "europe-west3" # Frankfurt - same as Qdrant
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "artifact_registry" {
  description = "Artifact Registry repository name"
  type        = string
  default     = "f1-agent"
}

# Qdrant Cloud variables
variable "qdrant_cloud_api_key" {
  description = "Qdrant Cloud API key (from cloud.qdrant.io > API Keys)"
  type        = string
  sensitive   = true
}

variable "qdrant_account_id" {
  description = "Qdrant Cloud Account ID (from cloud.qdrant.io > Account Settings)"
  type        = string
}

variable "qdrant_region" {
  description = "Qdrant Cloud region (GCP)"
  type        = string
  default     = "europe-west3" # Frankfurt
}

# Cloud Run deployment control
variable "deploy_cloud_run" {
  description = "Whether to deploy Cloud Run service (requires Docker image in Artifact Registry)"
  type        = bool
  default     = false
}
