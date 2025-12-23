<#
.SYNOPSIS
    Sets up GCP Workload Identity and GitHub Secrets for the F1 Penalty Agent.

.DESCRIPTION
    This script automates the creation of a GCP Service Account, Workload Identity Pool,
    and Provider, and then sets the necessary GitHub Secrets using the 'gh' CLI.
    
    Prerequisites:
    - gcloud CLI installed and authenticated
    - gh CLI installed and authenticated
    - User has 'Owner' or 'Editor' permissions on the GCP project

.EXAMPLE
    .\scripts\setup_gh_secrets.ps1
#>

$ErrorActionPreference = "Stop"

function Write-Color {
    param(
        [string]$Message,
        [string]$Color = "Cyan"
    )
    Write-Host "$Message" -ForegroundColor $Color
}

function Check-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Color "Error: '$Name' is not installed or not in PATH." "Red"
        exit 1
    }
}

# --- 1. Pre-flight Checks ---
Write-Color "Checking prerequisites..."
Check-Command "gcloud"
Check-Command "gh"

# Ensure user is logged in (basic check)
try {
    $currentProject = gcloud config get-value project 2>$null
}
catch {
    Write-Color "Error running gcloud. Please run 'gcloud auth login' first." "Red"
    exit 1
}

if ([string]::IsNullOrWhiteSpace($currentProject)) {
    Write-Color "No GCP project selected. Please run 'gcloud config set project <PROJECT_ID>'." "Red"
    exit 1
}

Write-Color "Current GCP Project: $currentProject" "Green"
$confirmation = Read-Host "Proceed with this project? (y/n)"
if ($confirmation -ne "y") {
    Write-Color "Aborted." "Yellow"
    exit 0
}

# --- 2. Configuration Variables ---
$PROJECT_ID = $currentProject
$SERVICE_ACCOUNT_NAME = "f1-agent-deployer"
$SERVICE_ACCOUNT_EMAIL = "$SERVICE_ACCOUNT_NAME@$PROJECT_ID.iam.gserviceaccount.com"
$POOL_NAME = "github-actions-pool"
$PROVIDER_NAME = "github-actions-provider"
$REPO_NAME = "KevNev19/f1-penalty-agent" # Change this if forking!

# --- 3. Enable APIs ---
Write-Color "Enabling required GCP APIs..."
gcloud services enable iam.googleapis.com iamcredentials.googleapis.com cloudresourcemanager.googleapis.com run.googleapis.com artifactregistry.googleapis.com
if ($LASTEXITCODE -ne 0) { exit 1 }

# --- 4. Create Service Account ---
Write-Color "Creating Service Account: $SERVICE_ACCOUNT_NAME..."
$ErrorActionPreference = "Continue" # Relax for Describe/Create which checks stderr
gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Color "Service Account already exists. Skipping creation." "Yellow"
}
else {
    # If describe fails (throws error due to stderr), it means it doesn't exist
    gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME --display-name "GitHub Actions Deployer" 2>$null
    Write-Color "Service Account created." "Green"
}
$ErrorActionPreference = "Stop"

# --- 5. Grant Permissions ---
Write-Color "Granting IAM permissions..."
$roles = @("roles/run.admin", "roles/storage.admin", "roles/artifactregistry.admin", "roles/iam.serviceAccountUser")
$ErrorActionPreference = "Continue"
foreach ($role in $roles) {
    # Adding binding is idempotent
    gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" --role=$role --condition=None 2>$null | Out-Null
    Write-Host "Granted $role"
}
$ErrorActionPreference = "Stop"

# --- 6. Create Workload Identity Pool ---
Write-Color "Creating Workload Identity Pool: $POOL_NAME..."
# Move project number fetch up
$PROJECT_NUMBER = gcloud projects describe $PROJECT_ID --format="value(projectNumber)"

$ErrorActionPreference = "Continue"
gcloud iam workload-identity-pools describe $POOL_NAME --location="global" 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Color "Pool already exists. Skipping." "Yellow"
}
else {
    gcloud iam workload-identity-pools create $POOL_NAME --location="global" --display-name="GitHub Actions Pool" 2>$null
    Write-Color "Pool created." "Green"
}
$ErrorActionPreference = "Stop"

# --- 7. Create Provider ---
Write-Color "Creating Workload Identity Provider: $PROVIDER_NAME..."
$ErrorActionPreference = "Continue"
gcloud iam workload-identity-pools providers describe $PROVIDER_NAME --workload-identity-pool=$POOL_NAME --location="global" 2>$null | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Color "Provider already exists. Skipping." "Yellow"
}
else {
    # Note: Use single quotes for attribute-mapping to prevent PowerShell parsing issues
    gcloud iam workload-identity-pools providers create-oidc $PROVIDER_NAME `
        --workload-identity-pool=$POOL_NAME `
        --location="global" `
        --display-name="GitHub Actions Provider" `
        --attribute-mapping='google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository' `
        --issuer-uri="https://token.actions.githubusercontent.com" 2>$null
    Write-Color "Provider created." "Green"
}
$ErrorActionPreference = "Stop"

# --- 8. Allow GitHub Repo to Impersonate SA ---
Write-Color "Binding Service Account to GitHub Repo..."
# Note: Check if binding exists to avoid error? gcloud usually handles idempotency gracefully for bindings 
# but for service account IAM policy binding, we need to be careful.
# This command adds the binding.
gcloud iam service-accounts add-iam-policy-binding $SERVICE_ACCOUNT_EMAIL `
    --role="roles/iam.workloadIdentityUser" `
    --member="principalSet://iam.googleapis.com/projects/$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')/locations/global/workloadIdentityPools/$POOL_NAME/attribute.repository/$REPO_NAME" | Out-Null

# --- 9. Construct Provider Resource Name ---
$PROJECT_NUMBER = gcloud projects describe $PROJECT_ID --format="value(projectNumber)"
$WORKLOAD_IDENTITY_PROVIDER = "projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_NAME/providers/$PROVIDER_NAME"

Write-Color "------------------------------------------------"
Write-Color "Completed GCP Setup!" "Green"
Write-Color "Project ID: $PROJECT_ID"
Write-Color "Service Account: $SERVICE_ACCOUNT_EMAIL"
Write-Color "Provider: $WORKLOAD_IDENTITY_PROVIDER"
Write-Color "------------------------------------------------"

# --- 10. Set GitHub Secrets ---
$setSecrets = Read-Host "Do you want to upload these secrets to GitHub now? (y/n)"
if ($setSecrets -eq "y") {
    Write-Color "Setting GitHub Secrets using gh CLI..."
    
    gh secret set GCP_PROJECT_ID --body "$PROJECT_ID"
    Write-Host "Set GCP_PROJECT_ID"

    gh secret set GCP_SERVICE_ACCOUNT --body "$SERVICE_ACCOUNT_EMAIL"
    Write-Host "Set GCP_SERVICE_ACCOUNT"
    
    gh secret set GCP_WORKLOAD_IDENTITY_PROVIDER --body "$WORKLOAD_IDENTITY_PROVIDER"
    Write-Host "Set GCP_WORKLOAD_IDENTITY_PROVIDER"

    Write-Color "All secrets set successfully!" "Green"
}
else {
    Write-Color "Skipping secret upload. You can do it manually." "Yellow"
}
