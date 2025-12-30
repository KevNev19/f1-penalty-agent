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
  count       = var.skip_qdrant ? 0 : 1
  secret      = google_secret_manager_secret.qdrant_url.id
  secret_data = qdrant-cloud_accounts_cluster.f1_agent[0].url
}

resource "google_secret_manager_secret_version" "qdrant_api_key_version" {
  count       = var.skip_qdrant ? 0 : 1
  secret      = google_secret_manager_secret.qdrant_api_key.id
  secret_data = qdrant-cloud_accounts_database_api_key_v2.f1_agent_key[0].key
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

