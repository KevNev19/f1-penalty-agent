# Cloud Run configuration for F1 Penalty Agent
# Deploy with: terraform apply -var="deploy_cloud_run=true"
# 
# Note: Cloud Run requires the Docker image to exist in Artifact Registry.
# Set deploy_cloud_run=false (default) to create infrastructure without Cloud Run.
# After pushing the Docker image, run: terraform apply -var="deploy_cloud_run=true"

resource "google_cloud_run_v2_service" "f1_agent" {
  count    = var.deploy_cloud_run ? 1 : 0
  name     = "f1-penalty-agent"
  location = var.region

  template {
    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.artifact_registry}/f1-agent:latest"

      ports {
        container_port = 8000
      }

      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.google_api_key.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "QDRANT_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.qdrant_url.secret_id
            version = "latest"
          }
        }
      }

      env {
        name = "QDRANT_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.qdrant_api_key.secret_id
            version = "latest"
          }
        }
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      startup_probe {
        http_get {
          path = "/health"
        }
        initial_delay_seconds = 10
        period_seconds        = 3
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/health"
        }
        period_seconds = 30
      }
    }

    scaling {
      min_instance_count = 0 # Scale to zero when not in use
      max_instance_count = 3 # Max 3 instances for demo
    }

    service_account = google_service_account.f1_agent.email
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }
}

# Allow unauthenticated access to the API
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  count    = var.deploy_cloud_run ? 1 : 0
  name     = google_cloud_run_v2_service.f1_agent[0].name
  location = google_cloud_run_v2_service.f1_agent[0].location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Output the service URL (only if deployed)
output "api_url" {
  description = "URL of the deployed F1 Agent API (empty if deploy_cloud_run=false)"
  value       = var.deploy_cloud_run ? google_cloud_run_v2_service.f1_agent[0].uri : ""
}

