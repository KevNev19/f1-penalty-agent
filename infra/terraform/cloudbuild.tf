# Cloud Build trigger for deploying F1 Penalty Agent

# GitHub repository connection (managed via Cloud Build console)
# The connection and repository linking must be done manually in GCP Console
# as it requires OAuth authentication flow

# Cloud Build trigger for the f1-penalty-agent service
resource "google_cloudbuild_trigger" "deploy" {
  name        = "f1-penalty-agent-deploy"
  description = "Build and deploy F1 Penalty Agent to Cloud Run on push to main"
  location    = "global"

  # GitHub trigger configuration
  github {
    owner = var.github_owner
    name  = var.github_repo_name

    push {
      branch = "^main$"
    }
  }

  # Path filter - only trigger when these files change
  included_files = [
    "src/**",
    "Dockerfile",
    "pyproject.toml",
    "poetry.lock",
    "cloudbuild.yaml"
  ]

  # Use cloudbuild.yaml from the repository
  filename = "cloudbuild.yaml"

  # Substitution overrides
  substitutions = {
    _AR_HOSTNAME   = "${var.region}-docker.pkg.dev"
    _AR_REPOSITORY = var.artifact_registry
    _SERVICE_NAME  = "f1-penalty-agent"
    _DEPLOY_REGION = var.region
  }

  # Service account for Cloud Build
  service_account = "projects/${var.project_id}/serviceAccounts/${google_service_account.f1_agent.email}"

  depends_on = [
    google_project_service.cloudbuild,
    google_artifact_registry_repository.f1_agent,
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

# Output the trigger ID
output "cloudbuild_trigger_id" {
  description = "Cloud Build trigger ID"
  value       = google_cloudbuild_trigger.deploy.id
}
