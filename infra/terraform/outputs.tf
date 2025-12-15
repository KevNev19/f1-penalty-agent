output "project_id" {
  description = "GCP Project ID"
  value       = var.project_id
}

output "apis_enabled" {
  description = "List of enabled APIs"
  value = [
    google_project_service.aiplatform.service,
    google_project_service.generativelanguage.service,
    google_project_service.secretmanager.service,
  ]
}
