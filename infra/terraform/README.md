# Terraform - F1 Agent Infrastructure

Deploy F1 Penalty Agent infrastructure to GCP with Qdrant Cloud.

## Architecture

- **Qdrant Cloud** - Vector database in GCP Frankfurt (`europe-west3`)
- **GCP Infrastructure** - Artifact Registry, Secret Manager, Service Account
- **Cloud Run** - Optional, deployed separately after Docker image push

## Quick Start

### 1. Get Credentials

**Qdrant Cloud** (https://cloud.qdrant.io/):
- Create account → API Keys → Create key with "Manage clusters" permission
- Account Settings → Copy Account ID

### 2. Deploy Infrastructure

```bash
cd infra/terraform

# Set variables
export TF_VAR_project_id="your-gcp-project"
export TF_VAR_qdrant_cloud_api_key="your-qdrant-api-key"
export TF_VAR_qdrant_account_id="your-account-id"

terraform init
terraform apply
```

This creates:
- Qdrant Cloud cluster in Frankfurt
- GCP APIs, Artifact Registry, Secrets
- **No Cloud Run yet** (decoupled from code)

### 3. Deploy Application (Optional)

After pushing Docker image:
```bash
# Build and push
docker build -t europe-west3-docker.pkg.dev/$TF_VAR_project_id/f1-agent/f1-agent:latest .
docker push europe-west3-docker.pkg.dev/$TF_VAR_project_id/f1-agent/f1-agent:latest

# Deploy Cloud Run
terraform apply -var="deploy_cloud_run=true"
```

## CI/CD Integration

Infrastructure changes are managed via GitHub Actions (`.github/workflows/infrastructure.yml`):

| Event | Action |
|-------|--------|
| PR to `main` | Terraform Plan (comment on PR) |
| Push to `main` | Terraform Apply (requires `production` environment approval) |

### GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `GCP_PROJECT_ID` | GCP Project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload Identity Provider |
| `GCP_SERVICE_ACCOUNT` | Service Account for Terraform |
| `QDRANT_CLOUD_API_KEY` | Qdrant Cloud management API key |
| `QDRANT_ACCOUNT_ID` | Qdrant Cloud account ID |

### GitHub Environment

Create a `production` environment with protection rules (Settings → Environments).

## Resources

| Resource | Description |
|----------|-------------|
| `qdrant-cloud_accounts_cluster.f1_agent` | Qdrant cluster |
| `google_artifact_registry_repository.f1_agent` | Docker registry |
| `google_secret_manager_secret.*` | API keys |
| `google_cloud_run_v2_service.f1_agent` | API (if deploy_cloud_run=true) |

## Outputs

```bash
terraform output qdrant_cluster_url    # Qdrant endpoint
terraform output -raw qdrant_api_key   # Qdrant API key
terraform output artifact_registry     # Docker registry path
terraform output api_url               # Cloud Run URL (if deployed)
```

## Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `project_id` | GCP Project ID | (required) |
| `region` | GCP region | `europe-west3` |
| `qdrant_cloud_api_key` | Qdrant Cloud API key | (required) |
| `qdrant_account_id` | Qdrant Cloud account ID | (required) |
| `deploy_cloud_run` | Deploy Cloud Run service | `false` |
