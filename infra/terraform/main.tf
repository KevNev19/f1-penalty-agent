terraform {
  required_version = ">= 1.4.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    qdrant-cloud = {
      source  = "qdrant/qdrant-cloud"
      version = "~> 1.14"  # Pin to 1.14.x to avoid breaking changes
    }
  }

  # Remote state in GCS - run bootstrap/ first to create the bucket
  backend "gcs" {
    bucket = "gen-lang-client-0855046443-tfstate"
    prefix = "f1-agent"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Qdrant Cloud provider
# Requires QDRANT_CLOUD_API_KEY environment variable (or api_key argument)
provider "qdrant-cloud" {
  api_key    = var.qdrant_cloud_api_key
  account_id = var.qdrant_account_id
}
