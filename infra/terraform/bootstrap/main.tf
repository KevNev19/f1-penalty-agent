# Terraform Bootstrap - Create Remote State Bucket
# Run this FIRST to create the GCS bucket for storing Terraform state
#
# Usage:
#   cd infra/terraform/bootstrap
#   terraform init
#   terraform apply -var="project_id=YOUR_PROJECT_ID"
#
# After this succeeds, run the main terraform from infra/terraform/

terraform {
  required_version = ">= 1.4.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region for the bucket"
  type        = string
  default     = "europe-west3" # Frankfurt - consistent with main infrastructure
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "storage" {
  service            = "storage.googleapis.com"
  disable_on_destroy = false
}

# Create GCS bucket for Terraform state
resource "google_storage_bucket" "terraform_state" {
  name          = "${var.project_id}-tfstate"
  location      = var.region
  force_destroy = false

  # Prevent accidental deletion
  lifecycle {
    prevent_destroy = true
  }

  # Enable versioning for state history
  versioning {
    enabled = true
  }

  # Uses Google-managed encryption by default (no explicit config needed)

  # Lifecycle rule - keep 30 days of versions
  lifecycle_rule {
    condition {
      num_newer_versions = 30
    }
    action {
      type = "Delete"
    }
  }

  uniform_bucket_level_access = true

  depends_on = [google_project_service.storage]
}

output "state_bucket_name" {
  description = "Name of the GCS bucket for Terraform state"
  value       = google_storage_bucket.terraform_state.name
}

output "state_bucket_url" {
  description = "URL of the GCS bucket"
  value       = google_storage_bucket.terraform_state.url
}

output "backend_config" {
  description = "Backend configuration to add to main terraform"
  value       = <<-EOT
    # Add this to infra/terraform/main.tf after bootstrap completes:
    backend "gcs" {
      bucket = "${google_storage_bucket.terraform_state.name}"
      prefix = "f1-agent"
    }
  EOT
}
