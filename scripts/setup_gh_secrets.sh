#!/bin/bash
# Script to setup GCP Workload Identity and GitHub Secrets for F1 Penalty Agent
# Run this locally with gcloud and gh CLI installed and authenticated

set -e

# Configuration
PROJECT_ID="f1-penalty-agent-444711"  # Replace with actual Project ID if different
REGION="europe-west3"
REPO="KevNev19/f1-penalty-agent"
SERVICE_ACCOUNT="github-actions-sa"
WORKLOAD_IDENTITY_POOL="github-actions-pool"
WORKLOAD_IDENTITY_PROVIDER="github-actions-provider"

echo "🚀 Starting Setup for $PROJECT_ID..."

# 1. Enable APIs
echo "Enabling required APIs..."
gcloud services enable iamcredentials.googleapis.com \
    cloudresourcemanager.googleapis.com \
    secretmanager.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    --project "$PROJECT_ID"

# 2. Create Service Account
if ! gcloud iam service-accounts describe "$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com" --project "$PROJECT_ID" > /dev/null 2>&1; then
    echo "Creating Service Account..."
    gcloud iam service-accounts create "$SERVICE_ACCOUNT" \
        --display-name="GitHub Actions Service Account" \
        --project "$PROJECT_ID"
else
    echo "Service Account already exists."
fi

SA_EMAIL="$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com"

# 3. Create Workload Identity Pool
if ! gcloud iam workload-identity-pools describe "$WORKLOAD_IDENTITY_POOL" --project "$PROJECT_ID" --location="global" > /dev/null 2>&1; then
    echo "Creating Workload Identity Pool..."
    gcloud iam workload-identity-pools create "$WORKLOAD_IDENTITY_POOL" \
        --project "$PROJECT_ID" \
        --location="global" \
        --display-name="GitHub Actions Pool"
else
    echo "Workload Identity Pool already exists."
fi

# 4. Create Workload Identity Provider
if ! gcloud iam workload-identity-pools providers describe "$WORKLOAD_IDENTITY_PROVIDER" \
    --project "$PROJECT_ID" \
    --location="global" \
    --workload-identity-pool="$WORKLOAD_IDENTITY_POOL" > /dev/null 2>&1; then
    echo "Creating Workload Identity Provider..."
    gcloud iam workload-identity-pools providers create-oidc "$WORKLOAD_IDENTITY_PROVIDER" \
        --project "$PROJECT_ID" \
        --location="global" \
        --workload-identity-pool="$WORKLOAD_IDENTITY_POOL" \
        --display-name="GitHub Actions Provider" \
        --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
        --issuer-uri="https://token.actions.githubusercontent.com"
else
    echo "Workload Identity Provider already exists."
fi

# 5. Bind Service Account to Workload Identity
echo "Binding Service Account to Workload Identity..."
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
    --project "$PROJECT_ID" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/$WORKLOAD_IDENTITY_POOL/attribute.repository/$REPO"

# 6. Grant Permissions to Service Account
echo "Granting IAM roles to Service Account..."
ROLES=(
    "roles/run.admin"
    "roles/storage.admin"
    "roles/artifactregistry.admin"
    "roles/secretmanager.secretAccessor"
    "roles/iam.serviceAccountUser"
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:$SA_EMAIL" \
        --role="$role"
done

# 7. Set GitHub Secrets
echo "Setting GitHub Secrets..."
WIP_NAME="projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/$WORKLOAD_IDENTITY_POOL/providers/$WORKLOAD_IDENTITY_PROVIDER"

gh secret set GCP_PROJECT_ID --body "$PROJECT_ID" --repo "$REPO"
gh secret set GCP_SERVICE_ACCOUNT --body "$SA_EMAIL" --repo "$REPO"
gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER --body "$WIP_NAME" --repo "$REPO"

echo "✅ Setup Complete!"
echo "GCP_PROJECT_ID: $PROJECT_ID"
echo "GCP_SERVICE_ACCOUNT: $SA_EMAIL"
echo "GCP_WORKLOAD_IDENTITY_PROVIDER: $WIP_NAME"
