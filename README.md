# F1 Penalty Agent 🏎️

An AI-powered agent that explains Formula 1 penalties and regulations using RAG (Retrieval-Augmented Generation) with official FIA documents.

## Features

- 🔍 **Semantic Search** - Find relevant regulations using Qdrant vector search
- 🤖 **AI Explanations** - Natural language explanations using Gemini
- 🎯 **Cross-Encoder Re-ranking** - Improved precision with MS MARCO model
- 📄 **Official Sources** - Uses FIA documents and race data
- 🚀 **Cloud Native** - Deploys to Google Cloud Run

## Quick Start

### Prerequisites

- Python 3.12+
- [Google AI API key](https://aistudio.google.com/) (free)
- [Qdrant Cloud account](https://cloud.qdrant.io/) (free tier)

### Installation

```bash
# Clone repository
git clone https://github.com/KevNev19/f1-penalty-agent.git
cd f1-penalty-agent

# Install dependencies
pip install poetry
poetry install

# Configure environment
cp .env.example .env
# Edit .env and add:
#   GOOGLE_API_KEY=your_google_key
#   QDRANT_URL=https://your-cluster.cloud.qdrant.io
#   QDRANT_API_KEY=your_qdrant_key
```

### Run Locally

```bash
# Start API server
poetry run uvicorn src.api.main:app --reload

# API available at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### CLI Usage

```bash
# Check status of knowledge base
poetry run f1agent status

# Setup/index all 2025 data (default)
poetry run f1agent setup

# Setup with limited data (for testing)
poetry run f1agent setup --limit 3

# Ask a question
poetry run f1agent ask "Why did Verstappen get a penalty?"

# Interactive chat
poetry run f1agent chat
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ready` | GET | Readiness probe (checks Qdrant connection) |
| `/api/v1/ask` | POST | Ask a question about F1 penalties |
| `/api/v1/setup/status` | GET | Check if knowledge base is populated |
| `/api/v1/setup` | POST | Index sample data into knowledge base |
| `/docs` | GET | OpenAPI documentation |

### Example Requests

```bash
# Ask a question
curl -X POST "http://localhost:8000/api/v1/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the penalty for track limits?"}'

# Check setup status
curl http://localhost:8000/api/v1/setup/status

# Trigger data setup
curl -X POST "http://localhost:8000/api/v1/setup" \
  -H "Content-Type: application/json" \
  -d '{"reset": false, "limit": 3}'
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Google AI API key | Yes |
| `QDRANT_URL` | Qdrant Cloud cluster URL | Yes |
| `QDRANT_API_KEY` | Qdrant Cloud API key | Yes |
| `LLM_MODEL` | Gemini model | No (default: gemini-2.0-flash) |

## Project Structure

```
f1-penalty-agent/
├── .github/workflows/  # CI/CD pipelines
│   ├── ci.yml          # Lint, test, build
│   ├── deploy.yml      # Deploy to Cloud Run
│   ├── infrastructure.yml  # Terraform plan/apply
│   └── release.yml     # GitHub releases
├── src/
│   ├── api/            # FastAPI backend
│   │   └── routers/    # API endpoints (chat, health, setup)
│   ├── rag/            # Qdrant + retriever + reranker
│   ├── agent/          # F1Agent logic
│   ├── llm/            # Gemini client
│   ├── interface/      # CLI
│   ├── common/         # Shared utilities (sanitize_text, chunk_text)
│   └── data/           # FIA scraper, FastF1 loader, Jolpica client
├── infra/terraform/    # GCP infrastructure as code
├── tests/              # Unit + integration tests
└── Dockerfile          # Production container
```

## Deployment

### Automated Deployment (CI/CD)

Push to `main` branch triggers automatic deployment:
1. **CI** - Lint, tests, Docker build verification
2. **Deploy** - Build, verify container, push to Artifact Registry, deploy to Cloud Run

Infrastructure changes in `infra/terraform/` trigger:
1. **Plan** - Terraform plan on PRs
2. **Apply** - Terraform apply on merge to main (requires approval)

### Manual Deployment

```bash
cd infra/terraform

# Initialize and apply
terraform init
terraform apply -var="project_id=your-project"

# Set Google API key (Qdrant secrets are auto-populated by Terraform)
echo "your-google-key" | gcloud secrets versions add f1-agent-google-api-key --data-file=-
```

### GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `GCP_PROJECT_ID` | GCP Project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload Identity Provider |
| `GCP_SERVICE_ACCOUNT` | Service Account for deployment |
| `QDRANT_CLOUD_API_KEY` | Qdrant Cloud management API key |
| `QDRANT_ACCOUNT_ID` | Qdrant Cloud account ID |

## Development

```bash
# Run all tests
poetry run pytest tests/ -v

# Run unit tests only
poetry run pytest tests/ -m unit -v

# Lint code
poetry run ruff check src/ tests/

# Auto-fix lint issues
poetry run ruff check src/ tests/ --fix
```

## License

MIT
