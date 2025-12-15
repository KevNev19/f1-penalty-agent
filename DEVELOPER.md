# Developer Guide

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface                          │
│                    (CLI / Future: Web)                      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                       F1Agent                                │
│  - Query Classification (PENALTY/RULE/GENERAL)              │
│  - Context Retrieval                                         │
│  - Response Generation                                       │
└────────────┬─────────────────────────────────┬──────────────┘
             │                                 │
┌────────────▼────────────┐      ┌─────────────▼─────────────┐
│      F1Retriever        │      │      GeminiClient         │
│  - Document Chunking    │      │  - Chat Generation        │
│  - Context Building     │      │  - Streaming Support      │
│  - Race/Driver Extract  │      │  - Retry Logic (3x)       │
└────────────┬────────────┘      └───────────────────────────┘
             │
┌────────────▼────────────┐
│      VectorStore        │
│  - HttpClient (K8s)     │
│  - Gemini Embeddings    │
│  - Retry Logic (3x)     │
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│   ChromaDB (K8s Pod)    │
│  - Vector Storage       │
│  - Similarity Search    │
└─────────────────────────┘
```

## Setup Development Environment

### Prerequisites

- Python 3.12+
- Docker Desktop with Kubernetes enabled
- Poetry
- kubectl

### Install

```bash
# Install dependencies (including dev extras)
poetry install --extras dev

# Deploy ChromaDB
python scripts/setup_infra.py

# Port-forward (keep running in separate terminal)
kubectl port-forward -n f1-agent svc/chromadb 8000:8000

# Set up environment
cp .env.example .env
# Add your GOOGLE_API_KEY and optionally CHROMA_HOST=localhost
```

### Run Tests

```bash
# Unit tests only (43 tests, no external deps)
poetry run pytest tests/ -m unit -v

# Integration tests (requires ChromaDB + API key)
poetry run pytest tests/ -m integration -v

# All tests with coverage
poetry run pytest tests/ -v --cov=src

# Run specific test class
poetry run pytest tests/test_suite.py::TestQueryClassification -v
```

### Linting

```bash
# Check for linting errors
poetry run ruff check src/ tests/

# Auto-fix linting errors
poetry run ruff check src/ tests/ --fix

# Check code formatting
poetry run ruff format src/ tests/ --check

# Auto-format code
poetry run ruff format src/ tests/
```

**Note:** Linting is enforced in CI. PRs will fail if there are linting errors.

## CLI Commands

| Command | Description |
|---------|-------------|
| `setup --chroma-host localhost` | Download and index F1 data |
| `ask "question" --chroma-host localhost` | Ask a single question |
| `chat` | Interactive chat mode |
| `status` | Check indexed document counts |

**Tip:** Set `CHROMA_HOST=localhost` in `.env` to avoid `--chroma-host` flags.

## Key Components

### VectorStore (`src/rag/vectorstore.py`)

- **HttpClient Mode**: Connects to Kubernetes ChromaDB
- **PersistentClient Mode**: Local mode (not recommended on Windows)
- **GeminiEmbeddingFunction**: 768-dim embeddings via Gemini API
- **Retry Logic**: 3 attempts with exponential backoff for rate limits

### F1Agent (`src/agent/f1_agent.py`)

- Classifies queries into PENALTY_EXPLANATION, RULE_LOOKUP, or GENERAL
- Uses regex patterns for query classification
- Retrieves relevant context from VectorStore
- Generates viewer-friendly explanations

### F1Retriever (`src/rag/retriever.py`)

- Text chunking with overlap for context preservation
- Driver name extraction (Verstappen, Hamilton, etc.)
- Race/Grand Prix detection
- Multi-source context building (regulations, stewards, race data)

### GeminiClient (`src/llm/gemini_client.py`)

- Synchronous and streaming generation
- Rate limit handling with exponential backoff (3 retries)
- Lazy initialization
- Token counting

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GOOGLE_API_KEY` | Google AI API key | Yes | - |
| `CHROMA_HOST` | ChromaDB server host | No | None (local) |
| `CHROMA_PORT` | ChromaDB server port | No | 8000 |
| `LLM_MODEL` | Gemini model name | No | gemini-2.0-flash |
| `DATA_DIR` | Data storage directory | No | ./data |
| `LOG_LEVEL` | Logging level | No | INFO |

## Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| Configuration | 6 | Settings, paths, ChromaDB config |
| Logging | 3 | setup_logging, get_logger |
| Data Models | 3 | FIADocument, Document, SearchResult |
| Query Classification | 3 | Penalty, rule, general queries |
| Text Chunking | 3 | Short/long text, content preservation |
| Context Extraction | 4 | Driver, race, season extraction |
| Retrieval Context | 2 | Creation, empty context |
| Prompts | 3 | Existence, placeholders, enums |
| VectorStore | 1 | Initialization |
| GeminiClient | 2 | Init, API key validation |
| Infrastructure | 13 | OS detection, K8s manifest validation |
| **Total Unit** | **43** | |

## Troubleshooting

### ChromaDB Connection Issues

```bash
# Check pod status
kubectl get pods -n f1-agent

# View logs
kubectl logs -f deployment/chromadb -n f1-agent

# Restart port-forward
kubectl port-forward -n f1-agent svc/chromadb 8000:8000

# Check ChromaDB heartbeat
curl http://localhost:8000/api/v2/heartbeat
```

### Embedding Rate Limits

The Gemini free tier has rate limits. The code now includes automatic retry logic:
- 3 retry attempts with exponential backoff (1s, 2s, 4s)
- If you still hit limits, wait a few seconds between requests
- Consider upgrading to paid tier for production use

### Test Failures

```bash
# Run only failing tests
poetry run pytest tests/ --lf -v

# Run with verbose output
poetry run pytest tests/test_suite.py::TestName -v --tb=long
```
