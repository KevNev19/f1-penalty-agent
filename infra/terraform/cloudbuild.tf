# IAM permissions for GitHub Actions deployments
# Note: Cloud Build triggers have been removed - using GitHub Actions instead

# Grant service account permissions to deploy to Cloud Run
resource "google_project_iam_member" "cloudbuild_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.f1_agent.email}"
}

resource "google_project_iam_member" "cloudbuild_sa_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.f1_agent.email}"
}

# Grant SA access to push to Artifact Registry
resource "google_artifact_registry_repository_iam_member" "cloudbuild_push" {
  location   = google_artifact_registry_repository.f1_agent.location
  repository = google_artifact_registry_repository.f1_agent.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.f1_agent.email}"
}

# Grant SA access to read secrets
resource "google_project_iam_member" "cloudbuild_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.f1_agent.email}"
}

# Grant SA permission to write logs
resource "google_project_iam_member" "cloudbuild_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.f1_agent.email}"
}

# Grant SA access to deploy to Firebase
resource "google_project_iam_member" "cloudbuild_firebase_admin" {
  project = var.project_id
  role    = "roles/firebase.admin"
  member  = "serviceAccount:${google_service_account.f1_agent.email}"
}

# Grant SA access to Service Usage (required for some Firebase operations)
resource "google_project_iam_member" "cloudbuild_service_usage" {
  project = var.project_id
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = "serviceAccount:${google_service_account.f1_agent.email}"
}
