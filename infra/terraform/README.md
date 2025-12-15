# Terraform Configuration for F1 Penalty Agent

This directory contains Terraform configuration for cloud resources.

## Resources Managed

- Google Cloud Project configuration
- API enablement (Gemini API)
- Secret Manager for API keys (optional)

## Usage

```bash
# Initialize
terraform init

# Plan changes
terraform plan -var="project_id=YOUR_PROJECT_ID"

# Apply
terraform apply -var="project_id=YOUR_PROJECT_ID"
```

## Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `project_id` | GCP Project ID | Yes |
| `region` | GCP Region | No (default: us-central1) |
