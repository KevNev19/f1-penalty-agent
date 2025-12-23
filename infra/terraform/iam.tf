# Service account for F1 Agent Cloud Run service

resource "google_service_account" "f1_agent" {
  account_id   = "f1-agent-runner"
  display_name = "F1 Penalty Agent Cloud Run Service Account"
  description  = "Service account for running F1 Penalty Agent on Cloud Run"
}

# Artifact Registry for Docker images
resource "google_artifact_registry_repository" "f1_agent" {
  location      = var.region
  repository_id = var.artifact_registry
  description   = "Docker images for F1 Penalty Agent"
  format        = "DOCKER"
}

# Grant Cloud Run service account permission to pull images
resource "google_artifact_registry_repository_iam_member" "pull_access" {
  location   = google_artifact_registry_repository.f1_agent.location
  repository = google_artifact_registry_repository.f1_agent.name
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.f1_agent.email}"
}

output "artifact_registry" {
  description = "Artifact Registry path for Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry}"
}
