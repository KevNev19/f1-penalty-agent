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
└────────────┬────────────┘      └───────────────────────────┘
             │
┌────────────▼────────────┐
│      VectorStore        │
│  - HttpClient (K8s)     │
│  - Gemini Embeddings    │
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
poetry install
python scripts/setup_infra.py
kubectl port-forward -n f1-agent svc/chromadb 8000:8000
```

### Run Tests

```bash
# Unit tests only
poetry run pytest tests/ -m unit -v

# Integration tests (requires ChromaDB)
poetry run pytest tests/ -m integration -v

# All tests with coverage
poetry run pytest tests/ -v --cov=src
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `setup --chroma-host localhost` | Download and index F1 data |
| `ask "question" --chroma-host localhost` | Ask a single question |
| `chat` | Interactive chat mode |
| `status` | Check indexed document counts |

## Key Components

### VectorStore (`src/rag/vectorstore.py`)

- **HttpClient Mode**: Connects to Kubernetes ChromaDB
- **PersistentClient Mode**: Local mode (not recommended on Windows)
- **GeminiEmbeddingFunction**: 768-dim embeddings via Gemini API

### F1Agent (`src/agent/f1_agent.py`)

- Classifies queries into PENALTY, RULE, or GENERAL
- Retrieves relevant context from VectorStore
- Generates viewer-friendly explanations

### GeminiClient (`src/llm/gemini_client.py`)

- Synchronous and streaming generation
- Rate limit handling with exponential backoff
- Lazy initialization

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Google AI API key | Yes |
| `LLM_MODEL` | Model name (default: gemini-2.0-flash) | No |
| `DATA_DIR` | Data storage directory | No |

## Troubleshooting

### ChromaDB Connection Issues

```bash
# Check pod status
kubectl get pods -n f1-agent

# View logs
kubectl logs -f deployment/chromadb -n f1-agent

# Restart port-forward
kubectl port-forward -n f1-agent svc/chromadb 8000:8000
```

### Embedding Rate Limits

The Gemini free tier has rate limits. If you hit them:
- Wait a few seconds between requests
- Use batch operations where possible
- Consider upgrading to paid tier
