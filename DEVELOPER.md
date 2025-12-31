# Developer Guide

## Architecture (Hexagonal)

```
┌─────────────────────────────────────────────────────────────┐
│                   Primary Adapters (Inbound)                │
│        (CLI: src/adapters/inbound/cli)                      │
│        (API: src/adapters/inbound/api)                      │
│        (Frontend: frontend/ - React + Vite)                 │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Core Services                             │
│        AgentService (src/core/services/agent_service.py)    │
│        RetrievalService (src/core/services/retrieval_service.py) │
└────────────┬─────────────────────────────────┬──────────────┘
             │                                 │
┌────────────▼────────────┐      ┌─────────────▼─────────────┐
│    Ports (Interfaces)   │      │    Ports (Interfaces)     │
│    VectorStorePort      │      │    LLMPort                │
│    (src/core/ports/)    │      │    (src/core/ports/)      │
└────────────┬────────────┘      └─────────────┬─────────────┘
             │                                 │
┌────────────▼────────────┐      ┌─────────────▼─────────────┐
│  Secondary Adapters     │      │  Secondary Adapters       │
│  QdrantAdapter          │      │  GeminiAdapter            │
│  (src/adapters/outbound)│      │  (src/adapters/outbound)  │
└────────────┬────────────┘      └───────────────────────────┘
             │
┌────────────▼────────────┐
│      Qdrant Cloud       │
│  (Managed Vector DB)    │
│  GCP europe-west3       │
└─────────────────────────┘
```

## Setup Development Environment

### Prerequisites

- Python 3.12+ (a `.python-version` file pins 3.12.12 for pyenv users)
- Node.js 18+ (for frontend development)
- Poetry (Python dependency management)
- Google AI API key
- Qdrant Cloud account (free tier)

### Backend Setup

```bash
# Install dependencies
poetry install

# Set up environment
cp .env.example .env
# Add GOOGLE_API_KEY, QDRANT_URL, and QDRANT_API_KEY

# Start API server
poetry run uvicorn src.adapters.inbound.api.main:app --reload
# API available at http://localhost:8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
# UI available at http://localhost:5173
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
# Python - Check for errors
poetry run ruff check src/ tests/

# Python - Auto-fix
poetry run ruff check src/ tests/ --fix

# Python - Check formatting
poetry run ruff format src/ tests/ --check

# Frontend - Lint
cd frontend && npm run lint
```

## Key Components

### Backend Components

#### QdrantAdapter (`src/adapters/outbound/vector_store/qdrant_adapter.py`)

- **Gemini Embeddings**: 768-dim vectors via Google API
- **Collections**: Separate storage for regulations, stewards_decisions, race_data
- **Score filtering**: Removes low-relevance results (< 0.5)
- **Auto-collection creation**: Creates collections on first use
- **API**: Uses `query_points` (qdrant-client 1.16+)

#### CrossEncoderReranker (`src/core/services/reranker.py`)

- **MS MARCO MiniLM**: Optimized for passage re-ranking
- **Lazy loading**: Model loaded on first use
- **Precision boost**: +15-20% improvement
- **Note**: Disabled on Windows due to torch DLL issues

#### RetrievalService (`src/core/services/retrieval_service.py`)

- **Query expansion**: F1-specific synonyms
- **Keyword boosting**: Exact match scoring
- **Deduplication**: Removes redundant results

#### Common Utilities (`src/core/domain/utils.py`)

Shared helper functions used across CLI, API, and LLM:

- **`sanitize_text(text)`**: Removes BOM and non-ASCII characters for API-safe text
- **`chunk_text(text, chunk_size, overlap)`**: Splits text into overlapping chunks (1500 chars, 200 overlap) for better vector search

### Frontend Components

#### ChatInterface (`frontend/src/components/ChatInterface.tsx`)

Main chat component with F1 radio-style design:
- Message cards styled as "DRIVER" (user) and "RACE ENGINEER" (AI)
- Loading state with animated bouncing dots
- Markdown rendering with remark-gfm
- Source citations with clickable links
- Auto-scroll to latest messages

#### Navbar (`frontend/src/components/Navbar.tsx`)

Top navigation bar:
- PitWallAI logo display
- Glassmorphism background effect
- Responsive design

#### API Service (`frontend/src/services/api.ts`)

TypeScript API client:
- `askQuestion(question, history)` - Send question with conversation history
- `checkHealth()` - Backend health check
- `checkReadiness()` - Backend readiness probe

### FastAPI Backend (`src/adapters/inbound/api/`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ready` | GET | Readiness probe (checks Qdrant) |
| `/api/v1/ask` | POST | Ask a question |
| `/api/v1/setup/status` | GET | Check data population status |
| `/api/v1/setup` | POST | Index sample data |
| `/docs` | GET | OpenAPI documentation |

### CLI (`src/adapters/inbound/cli/commands.py`)

| Command | Description |
|---------|-------------|
| `f1agent status` | Check knowledge base status |
| `f1agent setup` | Index sample data |
| `f1agent ask "..."` | Ask a single question |
| `f1agent chat` | Interactive chat session |

## Frontend Design System

### Color Palette

```css
/* Tailwind config extends */
f1-red: '#E10600'    /* Primary accent */
f1-black: '#15151E'  /* Backgrounds */
f1-grey: '#38383F'   /* Secondary backgrounds */
f1-silver: '#F0F0F0' /* Light text */
```

### Key UI Patterns

- **Glassmorphism**: `backdrop-blur-md bg-white/10 border border-white/20`
- **F1 Message Cards**: Rounded corners, left border accent, shadow
- **Radio-style Headers**: "DRIVER" and "RACE ENGINEER" labels
- **Live Indicators**: Animated pulse dots

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_API_KEY` | Google AI API key | Yes | - |
| `QDRANT_URL` | Qdrant Cloud cluster URL | Yes | - |
| `QDRANT_API_KEY` | Qdrant Cloud API key | Yes | - |
| `LLM_MODEL` | Gemini model | No | gemini-2.0-flash |
| `VITE_API_BASE_URL` | API URL for frontend | No | http://localhost:8000 |

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

### Running Both Services Locally

```bash
# Terminal 1: Backend
poetry run uvicorn src.adapters.inbound.api.main:app --reload

# Terminal 2: Frontend
cd frontend && npm run dev
```

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
