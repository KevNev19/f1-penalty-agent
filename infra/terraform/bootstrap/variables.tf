variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "europe-west3"
}

variable "github_owner" {
  description = "GitHub Organization or User name (e.g. KevNev19)"
  type        = string
}

variable "github_repo_name" {
  description = "GitHub Repository name (e.g. f1-penalty-agent)"
  type        = string
}

variable "github_token" {
  description = "GitHub PAT with repo scope to manage secrets"
  type        = string
  sensitive   = true
}

variable "qdrant_cloud_api_key" {
  description = "Qdrant Cloud API key for GitHub Actions"
  type        = string
  sensitive   = true
}

variable "qdrant_account_id" {
  description = "Qdrant Cloud Account ID for GitHub Actions"
  type        = string
}
