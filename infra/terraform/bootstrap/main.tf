terraform {
  required_version = ">= 1.4.6"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    github = {
      source  = "integrations/github"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "github" {
  owner = var.github_owner
  token = var.github_token
}

# --- APIs ---
resource "google_project_service" "required_apis" {
  for_each = toset([
    "serviceusage.googleapis.com",
    "storage.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com"
  ])
  service            = each.key
  disable_on_destroy = false
}

# --- State Bucket ---
resource "google_storage_bucket" "terraform_state" {
  name                        = "${var.project_id}-tfstate"
  location                    = var.region
  force_destroy               = false
  uniform_bucket_level_access = true

  lifecycle {
    prevent_destroy = true
  }
  versioning {
    enabled = true
  }
  lifecycle_rule {
    condition {
      num_newer_versions = 30
    }
    action {
      type = "Delete"
    }
  }
  depends_on = [google_project_service.required_apis]
}

# --- Service Account ---
resource "google_service_account" "deployer" {
  account_id   = "f1-agent-deployer"
  display_name = "GitHub Actions Deployer"
  depends_on   = [google_project_service.required_apis]
}

# --- IAM Roles for Service Account ---
resource "google_project_iam_member" "deployer_roles" {
  for_each = toset([
    "roles/run.admin",
    "roles/storage.admin",
    "roles/artifactregistry.admin",
    "roles/iam.serviceAccountUser",
    # Required for CI/CD infrastructure management:
    "roles/iam.serviceAccountAdmin",         # Create SAs
    "roles/resourcemanager.projectIamAdmin", # Grant roles to SAs
    "roles/secretmanager.admin",             # Manage secrets
    "roles/serviceusage.serviceUsageAdmin",  # Enable/list APIs
    "roles/cloudbuild.builds.editor"         # Create/manage Cloud Build triggers
  ])
  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.deployer.email}"
}


# --- Workload Identity Pool ---
resource "google_iam_workload_identity_pool" "github_pool" {
  workload_identity_pool_id = "github-actions-pool"
  display_name              = "GitHub Actions Pool"
  description               = "Identity pool for GitHub Actions"
  disabled                  = false
  depends_on                = [google_project_service.required_apis]
}

# --- Workload Identity Provider ---
resource "google_iam_workload_identity_pool_provider" "github_provider" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-actions-provider"
  display_name                       = "GitHub Actions Provider"
  description                        = "OIDC provider for GitHub Actions"

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.actor"      = "assertion.actor"
    "attribute.repository" = "assertion.repository"
  }

  # Security hardening: restrict access to this specific repository
  attribute_condition = "attribute.repository == \"${var.github_owner}/${var.github_repo_name}\""

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# --- Allow GitHub Repo to Impersonate SA ---
resource "google_service_account_iam_member" "workload_identity_user" {
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github_pool.name}/attribute.repository/${var.github_owner}/${var.github_repo_name}"
}

# --- GitHub Secrets ---
resource "github_actions_secret" "gcp_project_id" {
  repository      = var.github_repo_name
  secret_name     = "GCP_PROJECT_ID"
  plaintext_value = var.project_id
}

resource "github_actions_secret" "gcp_service_account" {
  repository      = var.github_repo_name
  secret_name     = "GCP_SERVICE_ACCOUNT"
  plaintext_value = google_service_account.deployer.email
}

resource "github_actions_secret" "gcp_workload_identity_provider" {
  repository      = var.github_repo_name
  secret_name     = "GCP_WORKLOAD_IDENTITY_PROVIDER"
  plaintext_value = google_iam_workload_identity_pool_provider.github_provider.name
}

# --- Qdrant Cloud Secrets ---
resource "github_actions_secret" "qdrant_cloud_api_key" {
  repository      = var.github_repo_name
  secret_name     = "QDRANT_CLOUD_API_KEY"
  plaintext_value = var.qdrant_cloud_api_key
}

resource "github_actions_secret" "qdrant_account_id" {
  repository      = var.github_repo_name
  secret_name     = "QDRANT_ACCOUNT_ID"
  plaintext_value = var.qdrant_account_id
}
