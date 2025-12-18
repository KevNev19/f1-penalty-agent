# F1 Penalty Agent 🏎️

An AI-powered agent that explains Formula 1 penalties and regulations to fans using RAG (Retrieval-Augmented Generation) with official FIA documents.

[![CI](https://github.com/KevNev19/f1-penalty-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/KevNev19/f1-penalty-agent/actions/workflows/ci.yml)

## Features

- 🔍 **Semantic Search** - Find relevant regulations and stewards' decisions
- 🤖 **AI Explanations** - Natural language explanations of penalties using Gemini
- 📄 **Official Sources** - Uses FIA documents and race data
- 💻 **Local First** - Works out-of-box with embedded ChromaDB (no Docker required)
- ☸️ **Kubernetes Ready** - Optional deployment to Docker Desktop Kubernetes
- 🔄 **Retry Logic** - Exponential backoff for API rate limits

## Production Roadmap 🚀

We are actively working on moving this POC to production. See [PRODUCTION_ROADMAP.md](PRODUCTION_ROADMAP.md) for full details.

### Key Work Items

| Area | Issue | Priority |
|------|-------|----------|
| **Accuracy** | [Upgrade Embedding Model](https://github.com/KevNev19/f1-penalty-agent/issues/20) | High |
| **Accuracy** | [Cross-Encoder Re-Ranking](https://github.com/KevNev19/f1-penalty-agent/issues/21) | High |
| **Accuracy** | [Improve Chunking](https://github.com/KevNev19/f1-penalty-agent/issues/26) | Medium |
| **Data** | [Fix Stewards Decisions 2025](https://github.com/KevNev19/f1-penalty-agent/issues/17) | Critical |
| **Data** | [Multi-Season Support](https://github.com/KevNev19/f1-penalty-agent/issues/25) | Medium |
| **Performance** | [Implement Caching](https://github.com/KevNev19/f1-penalty-agent/issues/22) | High |
| **Performance** | [Streaming Responses](https://github.com/KevNev19/f1-penalty-agent/issues/18) | Medium |
| **Architecture** | [Migrate to FastAPI + React](https://github.com/KevNev19/f1-penalty-agent/issues/19) | Long Term |

## Demo

![F1 Penalty Agent Demo](docs/assets/demo.webp)

*The Streamlit chat interface with ChromaDB running in local mode*

## Quick Start

### Prerequisites

- Python 3.12+
- Google AI API key ([get one free](https://aistudio.google.com/))
- Docker (optional, for running ChromaDB in container)

### Installation

**Automated Setup (Recommended)**

```bash
# Clone repository
git clone https://github.com/KevNev19/f1-penalty-agent.git
cd f1-penalty-agent

# Mac/Linux
chmod +x scripts/setup.sh && ./scripts/setup.sh

# Windows (PowerShell)
.\scripts\setup.ps1
```

The setup script will:
- ✓ Check all prerequisites (Python 3.12+, Poetry, Docker, kubectl)
- ✓ Show what's missing with install commands
- ✓ Create `.env` from template
- ✓ Install Python dependencies

**Manual Setup**

```bash
# Install dependencies
pip install poetry
poetry install

# Configure API key
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### Infrastructure Setup

```bash
# Deploy ChromaDB to Kubernetes
python scripts/setup_infra.py

# In a separate terminal, port-forward ChromaDB
kubectl port-forward -n f1-agent svc/chromadb 8000:8000
```

### Data Setup

```bash
# Download and index F1 documents (uses local ChromaDB by default)
poetry run f1agent setup

# Or with K8s ChromaDB (if running separately)
poetry run f1agent setup --chroma-host localhost
```

### Usage

```bash
# Ask a single question
poetry run python -m src.interface.cli ask "Why did Verstappen get a penalty?" --chroma-host localhost

# Interactive chat (uses CHROMA_HOST from .env if set)
poetry run python -m src.interface.cli chat

# Check data status
poetry run python -m src.interface.cli status
```

### Web UI (Streamlit)

```bash
# Start the web interface (uses local ChromaDB by default)
streamlit run app.py
```

Visit **http://localhost:8501** for the chat interface.

## Environment Variables

Instead of CLI flags, you can set these in `.env`:

```bash
GOOGLE_API_KEY=your_key_here
CHROMA_HOST=localhost  # For K8s mode
CHROMA_PORT=8000
```

## Example Questions

- "Why did Hamilton get a 5-second penalty in Monaco?"
- "What is the rule for track limits?"
- "Explain the unsafe release penalty"
- "What happens if a driver exceeds 107%?"

## Project Structure

```
f1-penalty-agent/
├── src/
│   ├── agent/         # AI agent logic and prompts
│   ├── config.py      # Configuration (pydantic-settings)
│   ├── data/          # FIA scraper, FastF1 loader
│   ├── interface/     # CLI interface (Typer)
│   ├── llm/           # Gemini API client with retry logic
│   ├── logging_config.py  # Structured logging
│   └── rag/           # VectorStore, Retriever
├── infra/
│   ├── k8s/           # Kubernetes manifests
│   └── terraform/     # GCP resources (optional)
├── scripts/           # Cross-platform setup script
├── tests/             # 98 unit tests, integration tests
└── .github/workflows/ # CI pipeline
```

## Development

```bash
# Run unit tests (98 tests)
poetry run pytest tests/ -m unit -v

# Run integration tests (requires ChromaDB)
poetry run pytest tests/ -m integration -v

# Run all tests
poetry run pytest tests/ -v
```

## License

MIT
