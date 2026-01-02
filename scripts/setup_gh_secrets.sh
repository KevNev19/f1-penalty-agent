#!/bin/bash
# Script to setup GCP Workload Identity and GitHub Secrets for F1 Penalty Agent
# Run this locally with gcloud and gh CLI installed and authenticated

set -e

# --- 1. Pre-flight Checks ---
echo "Checking prerequisites..."
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud is not installed or not in PATH."
    exit 1
fi

if ! command -v gh &> /dev/null; then
    echo "Error: gh is not installed or not in PATH."
    exit 1
fi

# Ensure user is logged in (basic check)
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -z "$CURRENT_PROJECT" ]; then
    echo "Error: No GCP project selected. Please run 'gcloud auth login' and 'gcloud config set project <PROJECT_ID>'."
    exit 1
fi

echo -e "\033[32mCurrent GCP Project: $CURRENT_PROJECT\033[0m"
read -p "Proceed with this project? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# --- 2. Configuration Variables ---
PROJECT_ID="$CURRENT_PROJECT"
SERVICE_ACCOUNT_NAME="f1-agent-deployer"
SERVICE_ACCOUNT_EMAIL="$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"
POOL_NAME="github-actions-pool"
PROVIDER_NAME="github-actions-provider"
REPO_NAME="KevNev19/f1-penalty-agent" # Change this if forking!

# --- 3. Enable APIs ---
echo "Enabling required GCP APIs..."
gcloud services enable iam.googleapis.com iamcredentials.googleapis.com cloudresourcemanager.googleapis.com run.googleapis.com artifactregistry.googleapis.com

# --- 4. Create Service Account ---
echo "Creating Service Account: $SERVICE_ACCOUNT_NAME..."
EXISTING_SA=$(gcloud iam service-accounts list --filter="email:$SERVICE_ACCOUNT_EMAIL" --format="value(email)")

if [ -z "$EXISTING_SA" ]; then
    gcloud iam service-accounts create "$SERVICE_ACCOUNT_NAME" --display-name "GitHub Actions Deployer"
    echo -e "\033[32mService Account created.\033[0m"
else
    echo -e "\033[33mService Account already exists. Skipping creation.\033[0m"
fi

# --- 5. Grant Permissions ---
echo "Granting IAM permissions..."
ROLES=("roles/run.admin" "roles/storage.admin" "roles/artifactregistry.admin" "roles/iam.serviceAccountUser")

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role="$role" --condition=None > /dev/null
    echo "Granted $role"
done

# --- 6. Create Workload Identity Pool ---
echo "Creating Workload Identity Pool: $POOL_NAME..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
EXISTING_POOL=$(gcloud iam workload-identity-pools list --location="global" --filter="name:projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_NAME" --format="value(name)")

if [ -z "$EXISTING_POOL" ]; then
    gcloud iam workload-identity-pools create "$POOL_NAME" --location="global" --display-name="GitHub Actions Pool"
    echo -e "\033[32mPool created.\033[0m"
else
    echo -e "\033[33mPool already exists. Skipping.\033[0m"
fi

# --- 7. Create Provider ---
echo "Creating Workload Identity Provider: $PROVIDER_NAME..."
EXISTING_PROVIDER=$(gcloud iam workload-identity-pools providers list --workload-identity-pool="$POOL_NAME" --location="global" --filter="name:projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_NAME/providers/$PROVIDER_NAME" --format="value(name)")

if [ -z "$EXISTING_PROVIDER" ]; then
    gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_NAME" \
        --workload-identity-pool="$POOL_NAME" \
        --location="global" \
        --display-name="GitHub Actions Provider" \
        --attribute-mapping='google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository' \
        --issuer-uri="https://token.actions.githubusercontent.com"
    echo -e "\033[32mProvider created.\033[0m"
else
    echo -e "\033[33mProvider already exists. Skipping.\033[0m"
fi

# --- 8. Allow GitHub Repo to Impersonate SA ---
echo "Binding Service Account to GitHub Repo..."
gcloud iam service-accounts add-iam-policy-binding "$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_NAME/attribute.repository/$REPO_NAME" > /dev/null

# --- 9. Construct Provider Resource Name ---
WORKLOAD_IDENTITY_PROVIDER="projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_NAME/providers/$PROVIDER_NAME"

echo "------------------------------------------------"
echo -e "\033[32mCompleted GCP Setup!\033[0m"
echo "Project ID: $PROJECT_ID"
echo "Service Account: $SERVICE_ACCOUNT_EMAIL"
echo "Provider: $WORKLOAD_IDENTITY_PROVIDER"
echo "------------------------------------------------"

# --- 10. Set GitHub Secrets ---
read -p "Do you want to upload these secrets to GitHub now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Setting GitHub Secrets using gh CLI..."

    gh secret set GCP_PROJECT_ID --body "$PROJECT_ID"
    echo "Set GCP_PROJECT_ID"

    gh secret set GCP_SERVICE_ACCOUNT --body "$SERVICE_ACCOUNT_EMAIL"
    echo "Set GCP_SERVICE_ACCOUNT"

    gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER --body "$WORKLOAD_IDENTITY_PROVIDER"
    echo "Set GCP_WORKLOAD_IDENTITY_PROVIDER"

    echo -e "\033[32mAll secrets set successfully!\033[0m"
else
    echo -e "\033[33mSkipping secret upload. You can do it manually.\033[0m"
fi
