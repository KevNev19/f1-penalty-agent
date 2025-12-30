# Cloud Build trigger for deploying PitWallAI

# GitHub repository connection (managed via Cloud Build console)
# The connection and repository linking must be done manually in GCP Console
# as it requires OAuth authentication flow

# =============================================================================
# Backend Trigger: PitWallAI API (Cloud Run)
# =============================================================================
resource "google_cloudbuild_trigger" "backend" {
  name        = "pitwall-api-deploy"
  description = "Build and deploy PitWallAI API to Cloud Run on push to main"
  location    = "global"

  # GitHub trigger configuration
  github {
    owner = var.github_owner
    name  = var.github_repo_name

    push {
      branch = "^main$"
    }
  }

  # Path filter - only trigger when backend files change
  included_files = [
    "src/**",
    "Dockerfile",
    "pyproject.toml",
    "poetry.lock",
    "cloudbuild-backend.yaml"
  ]

  # Use backend-specific cloudbuild file
  filename = "cloudbuild-backend.yaml"

  # Substitution overrides
  substitutions = {
    _AR_HOSTNAME   = "${var.region}-docker.pkg.dev"
    _AR_REPOSITORY = var.artifact_registry
    _SERVICE_NAME  = "pitwall-api"
    _DEPLOY_REGION = var.region
  }

  # Service account for Cloud Build
  service_account = "projects/${var.project_id}/serviceAccounts/${google_service_account.f1_agent.email}"

  depends_on = [
    google_project_service.cloudbuild,
    google_artifact_registry_repository.f1_agent,
  ]
}

# =============================================================================
# Frontend Trigger: PitWallAI Web (Firebase Hosting)
# =============================================================================
resource "google_cloudbuild_trigger" "frontend" {
  name        = "pitwall-web-deploy"
  description = "Build and deploy PitWallAI frontend to Firebase Hosting on push to main"
  location    = "global"

  # GitHub trigger configuration
  github {
    owner = var.github_owner
    name  = var.github_repo_name

    push {
      branch = "^main$"
    }
  }

  # Path filter - only trigger when frontend files change
  included_files = [
    "frontend/**",
    "firebase.json",
    ".firebaserc",
    "cloudbuild-frontend.yaml"
  ]

  # Use frontend-specific cloudbuild file
  filename = "cloudbuild-frontend.yaml"

  # Service account for Cloud Build
  service_account = "projects/${var.project_id}/serviceAccounts/${google_service_account.f1_agent.email}"

  depends_on = [
    google_project_service.cloudbuild,
  ]
}

# Grant Cloud Build service account permissions to deploy to Cloud Run
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

# Grant Cloud Build SA access to push to Artifact Registry
resource "google_artifact_registry_repository_iam_member" "cloudbuild_push" {
  location   = google_artifact_registry_repository.f1_agent.location
  repository = google_artifact_registry_repository.f1_agent.name
  role       = "roles/artifactregistry.writer"
  member     = "serviceAccount:${google_service_account.f1_agent.email}"
}

# Grant Cloud Build SA access to read secrets
resource "google_project_iam_member" "cloudbuild_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.f1_agent.email}"
}

# Grant Cloud Build SA permission to write logs
resource "google_project_iam_member" "cloudbuild_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.f1_agent.email}"
}

# Grant Cloud Build SA access to deploy to Firebase
resource "google_project_iam_member" "cloudbuild_firebase_admin" {
  project = var.project_id
  role    = "roles/firebase.admin"
  member  = "serviceAccount:${google_service_account.f1_agent.email}"
}

# Grant Cloud Build SA access to Service Usage (required for some Firebase operations)
resource "google_project_iam_member" "cloudbuild_service_usage" {
  project = var.project_id
  role    = "roles/serviceusage.serviceUsageConsumer"
  member  = "serviceAccount:${google_service_account.f1_agent.email}"
}

# Output the trigger IDs
output "cloudbuild_backend_trigger_id" {
  description = "Cloud Build backend trigger ID"
  value       = google_cloudbuild_trigger.backend.id
}

output "cloudbuild_frontend_trigger_id" {
  description = "Cloud Build frontend trigger ID"
  value       = google_cloudbuild_trigger.frontend.id
}
