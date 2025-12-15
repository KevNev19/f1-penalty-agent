# Infrastructure Directory

This directory contains all infrastructure-as-code for the F1 Penalty Agent.

## Prerequisites

- **Docker Desktop** with Kubernetes enabled
- No additional tools needed (k3d not required)

## Quick Start

```bash
# Run cross-platform setup script
python scripts/setup_infra.py

# Check prerequisites only
python scripts/setup_infra.py --check

# Remove resources
python scripts/setup_infra.py --clean
```

## Enable Kubernetes in Docker Desktop

1. Open **Docker Desktop**
2. Go to **Settings** (⚙️)
3. Click **Kubernetes** in sidebar
4. Check **"Enable Kubernetes"**
5. Click **Apply & Restart**
6. Wait for green Kubernetes icon

## Port Forward ChromaDB

After setup, run in a separate terminal:
```bash
kubectl port-forward -n f1-agent svc/chromadb 8000:8000
```

ChromaDB available at: http://localhost:8000

## Directory Structure

```
infra/
├── k8s/                      # Kubernetes manifests
│   ├── namespace.yaml
│   └── chromadb/
│       └── deployment.yaml   # Deployment, Service, PVC
└── terraform/                # GCP resources (optional)
    ├── main.tf
    ├── variables.tf
    └── apis.tf
```

## Architecture

```
┌─────────────────────────────────────┐
│      Docker Desktop Kubernetes      │
│  ┌───────────────────────────────┐  │
│  │       f1-agent namespace      │  │
│  │  ┌─────────────────────────┐  │  │
│  │  │  ChromaDB (Port 8000)   │  │  │
│  │  └─────────────────────────┘  │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
         │ kubectl port-forward
         ▼
┌─────────────────────┐
│   Python Agent      │──► Google Gemini API
└─────────────────────┘
```
