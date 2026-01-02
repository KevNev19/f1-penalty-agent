# Secret Manager secrets for F1 Agent

resource "google_secret_manager_secret" "google_api_key" {
  secret_id = "f1-agent-google-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret" "qdrant_url" {
  secret_id = "f1-agent-qdrant-url"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret" "qdrant_api_key" {
  secret_id = "f1-agent-qdrant-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

# Auto-populate Qdrant secrets from Terraform-created cluster
resource "google_secret_manager_secret_version" "qdrant_url_version" {
  secret      = google_secret_manager_secret.qdrant_url.id
  secret_data = qdrant-cloud_accounts_cluster.f1_agent.url
}

resource "google_secret_manager_secret_version" "qdrant_api_key_version" {
  secret      = google_secret_manager_secret.qdrant_api_key.id
  secret_data = qdrant-cloud_accounts_database_api_key_v2.f1_agent_key.key
}

# Grant Cloud Run service account access to secrets
resource "google_secret_manager_secret_iam_member" "google_api_key_access" {
  secret_id = google_secret_manager_secret.google_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.f1_agent.email}"
}

resource "google_secret_manager_secret_iam_member" "qdrant_url_access" {
  secret_id = google_secret_manager_secret.qdrant_url.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.f1_agent.email}"
}

resource "google_secret_manager_secret_iam_member" "qdrant_api_key_access" {
  secret_id = google_secret_manager_secret.qdrant_api_key.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.f1_agent.email}"
}

# Output secret IDs
output "google_api_key_secret" {
  description = "Secret Manager ID for Google API key - populate with: gcloud secrets versions add f1-agent-google-api-key --data-file=-"
  value       = google_secret_manager_secret.google_api_key.secret_id
}

output "qdrant_url_secret" {
  description = "Secret Manager ID for Qdrant URL (auto-populated from Terraform)"
  value       = google_secret_manager_secret.qdrant_url.secret_id
}

output "qdrant_api_key_secret" {
  description = "Secret Manager ID for Qdrant API key (auto-populated from Terraform)"
  value       = google_secret_manager_secret.qdrant_api_key.secret_id
}

# =============================================================================
# GitHub Secrets (synced to GitHub via sync-secrets.yml workflow)
# =============================================================================

# Firebase service account key for GitHub Actions to deploy to Firebase Hosting
# Note: The secret version is created manually via gcloud, not Terraform,
# because the key is generated separately
resource "google_secret_manager_secret" "github_firebase_sa" {
  secret_id = "github-firebase-service-account"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

resource "google_secret_manager_secret_iam_member" "github_firebase_sa_access" {
  secret_id = google_secret_manager_secret.github_firebase_sa.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.f1_agent.email}"
}

# GitHub secret for Qdrant Cloud API key (for CI/CD Terraform runs)
resource "google_secret_manager_secret" "github_qdrant_cloud_api_key" {
  secret_id = "github-qdrant-cloud-api-key"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}

# GitHub secret for Qdrant Account ID (for CI/CD Terraform runs)
resource "google_secret_manager_secret" "github_qdrant_account_id" {
  secret_id = "github-qdrant-account-id"

  replication {
    auto {}
  }

  depends_on = [google_project_service.secretmanager]
}
