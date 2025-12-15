# Enable required Google Cloud APIs
resource "google_project_service" "aiplatform" {
  service            = "aiplatform.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "generativelanguage" {
  service            = "generativelanguage.googleapis.com"
  disable_on_destroy = false
}

# Optional: Secret Manager for API keys
resource "google_project_service" "secretmanager" {
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

# Optional: Store API key in Secret Manager
# resource "google_secret_manager_secret" "gemini_api_key" {
#   secret_id = "gemini-api-key"
#
#   replication {
#     auto {}
#   }
#
#   depends_on = [google_project_service.secretmanager]
# }
#
# resource "google_secret_manager_secret_version" "gemini_api_key" {
#   secret      = google_secret_manager_secret.gemini_api_key.id
#   secret_data = var.gemini_api_key  # Pass via TF_VAR_gemini_api_key
# }
