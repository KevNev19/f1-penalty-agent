# Developer Guide

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface                          │
│              (CLI / React Frontend / API)                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                     FastAPI Backend                          │
│  - Health/Ready endpoints                                    │
│  - /api/v1/ask endpoint                                      │
│  - /api/v1/setup endpoints                                   │
└────────────┬─────────────────────────────────┬──────────────┘
             │                                 │
┌────────────▼────────────┐      ┌─────────────▼─────────────┐
│       F1Retriever       │      │      GeminiClient         │
│  - Query expansion      │      │  - Chat Generation        │
│  - Cross-encoder rerank │      │  - Retry Logic (3x)       │
│  - Context building     │      └───────────────────────────┘
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│    QdrantVectorStore    │
│  - Gemini Embeddings    │
│  - Collection separation│
│  - Score filtering      │
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│      Qdrant Cloud       │
│  (Managed Vector DB)    │
│  GCP europe-west3       │
└─────────────────────────┘
```

## Setup Development Environment

### Prerequisites

- Python 3.12+
- Poetry
- Google AI API key
- Qdrant Cloud account (free tier)

### Install

```bash
# Install dependencies
poetry install

# Set up environment
cp .env.example .env
# Add GOOGLE_API_KEY, QDRANT_URL, and QDRANT_API_KEY
```

### Run Tests

```bash
# Unit tests (18+ tests)
poetry run pytest tests/ -m unit -v

# Integration tests
poetry run pytest tests/ -m integration -v

# All tests
poetry run pytest tests/ -v
```

### Linting

```bash
# Check for errors
poetry run ruff check src/ tests/

# Auto-fix
poetry run ruff check src/ tests/ --fix

# Check formatting
poetry run ruff format src/ tests/ --check
```

## Key Components

### QdrantVectorStore (`src/rag/qdrant_store.py`)

- **Gemini Embeddings**: 768-dim vectors via Google API
- **Collections**: Separate storage for regulations, stewards_decisions, race_data
- **Score filtering**: Removes low-relevance results (< 0.5)
- **Auto-collection creation**: Creates collections on first use
- **API**: Uses `query_points` (qdrant-client 1.16+)

### CrossEncoderReranker (`src/rag/reranker.py`)

- **MS MARCO MiniLM**: Optimized for passage re-ranking
- **Lazy loading**: Model loaded on first use
- **Precision boost**: +15-20% improvement
- **Note**: Disabled on Windows due to torch DLL issues

### F1Retriever (`src/rag/retriever.py`)

- **Query expansion**: F1-specific synonyms
- **Keyword boosting**: Exact match scoring
- **Deduplication**: Removes redundant results

### Common Utilities (`src/common/utils.py`)

Shared helper functions used across CLI, API, and LLM:

- **`sanitize_text(text)`**: Removes BOM and non-ASCII characters for API-safe text
- **`chunk_text(text, chunk_size, overlap)`**: Splits text into overlapping chunks (1500 chars, 200 overlap) for better vector search

### FastAPI Backend (`src/api/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ready` | GET | Readiness probe (checks Qdrant) |
| `/api/v1/ask` | POST | Ask a question |
| `/api/v1/setup/status` | GET | Check data population status |
| `/api/v1/setup` | POST | Index sample data |
| `/docs` | GET | OpenAPI documentation |

### CLI (`src/interface/cli.py`)

| Command | Description |
|---------|-------------|
| `f1agent status` | Check knowledge base status |
| `f1agent setup` | Index sample data |
| `f1agent ask "..."` | Ask a single question |
| `f1agent chat` | Interactive chat session |

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_API_KEY` | Google AI API key | Yes | - |
| `QDRANT_URL` | Qdrant Cloud cluster URL | Yes | - |
| `QDRANT_API_KEY` | Qdrant Cloud API key | Yes | - |
| `LLM_MODEL` | Gemini model | No | gemini-2.0-flash |

## CI/CD Workflows

### `ci.yml` - Continuous Integration
- **Trigger**: Push/PR to main, develop, feature/*
- **Jobs**: Lint, Unit Tests, Integration Tests, Docker Build, Package Build

### `deploy.yml` - Deploy to Cloud Run
- **Trigger**: Push to main (src changes)
- **Jobs**: Build → Verify Container → Push → Deploy

### `infrastructure.yml` - Terraform
- **Trigger**: Push/PR to main (infra changes)
- **Jobs**: Plan (on PR) → Apply (on merge, requires approval)

### `release.yml` - GitHub Release
- **Trigger**: Version tags (v*)
- **Jobs**: Build package → Create release

## Deployment

### Cloud Run (Automated)

Push to `main` triggers automatic deployment. Manual deployment:

```bash
cd infra/terraform
terraform init
terraform apply -var="project_id=YOUR_PROJECT" \
                -var="qdrant_cloud_api_key=YOUR_KEY" \
                -var="qdrant_account_id=YOUR_ACCOUNT"

# Set Google API key (Qdrant secrets auto-populated)
echo "your-google-key" | gcloud secrets versions add f1-agent-google-api-key --data-file=-
```

### GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `GCP_PROJECT_ID` | GCP Project ID |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Workload Identity Provider |
| `GCP_SERVICE_ACCOUNT` | Service Account |
| `QDRANT_URL` | Qdrant cluster URL (for tests) |
| `QDRANT_API_KEY` | Qdrant API key (for tests) |
| `QDRANT_CLOUD_API_KEY` | Qdrant management API key |
| `QDRANT_ACCOUNT_ID` | Qdrant account ID |

### GitHub Environments

Create `production` environment with protection rules for Terraform apply.

See `infra/terraform/` for full configuration.
