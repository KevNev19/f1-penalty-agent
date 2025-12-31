# PitWallAI 🏎️

Your official AI Race Engineer for Formula 1 - get real-time insights on penalties, regulations, and race strategy using RAG (Retrieval-Augmented Generation) with official FIA documents.

![PitWallAI Interface](frontend/public/bg-track.png)

## ✨ Features

### AI-Powered Race Intelligence
- 🔍 **Semantic Search** - Find relevant regulations using Qdrant vector search
- 🤖 **AI Explanations** - Natural language explanations using Gemini 2.0
- 🎯 **Cross-Encoder Re-ranking** - Improved precision with MS MARCO model
- 📄 **Official Sources** - Uses FIA regulations, stewards' decisions, and live race data
- 💬 **Conversational Memory** - Multi-turn conversations with context awareness

### Modern F1 Broadcast-Style UI
- 🎨 **F1 Visual Theme** - Authentic racing aesthetics with F1 red accents
- 📻 **Radio Message Cards** - Chat styled like team radio communications
- 🌌 **Glassmorphism Design** - Premium frosted glass effects throughout
- 📱 **Responsive Layout** - Works seamlessly on desktop and mobile
- 🖼️ **Track Background** - Immersive racing circuit backdrop

### Production-Ready Architecture
- 🚀 **Cloud Native** - Deploys to Google Cloud Run
- 🏗️ **Hexagonal Architecture** - Clean separation of concerns
- 🔄 **CI/CD Pipeline** - Automated testing and deployment
- 📊 **Infrastructure as Code** - Terraform-managed GCP resources

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+ (for frontend)
- [Google AI API key](https://aistudio.google.com/) (free)
- [Qdrant Cloud account](https://cloud.qdrant.io/) (free tier)

### Installation

```bash
# Clone repository
git clone https://github.com/KevNev19/pitwall-ai.git
cd pitwall-ai

# Install backend dependencies
pip install poetry
poetry install

# Install frontend dependencies
cd frontend
npm install
cd ..

# Configure environment
cp .env.example .env
# Edit .env and add:
#   GOOGLE_API_KEY=your_google_key
#   QDRANT_URL=https://your-cluster.cloud.qdrant.io
#   QDRANT_API_KEY=your_qdrant_key
```

### Run Locally

```bash
# Terminal 1: Start API server
poetry run uvicorn src.adapters.inbound.api.main:app --reload
# API available at http://localhost:8000

# Terminal 2: Start frontend
cd frontend
npm run dev
# UI available at http://localhost:5173
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

## 🎨 User Interface

The frontend features a premium F1 broadcast-inspired design:

| Component | Description |
|-----------|-------------|
| **Header** | PitWallAI logo with animated tagline |
| **Chat Interface** | F1 radio-style message cards with driver/engineer labels |
| **Message Cards** | Glassmorphism effects with live indicators |
| **Input Area** | Rounded input with F1 red send button |
| **Background** | Circuit track image with dark overlay |

### Tech Stack (Frontend)
- **React 18** + TypeScript
- **Vite** for fast development
- **TailwindCSS** for styling
- **React Markdown** for formatted responses

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/ready` | GET | Readiness probe (checks Qdrant connection) |
| `/api/v1/ask` | POST | Ask a question to PitWallAI |
| `/api/v1/setup/status` | GET | Check if knowledge base is populated |
| `/api/v1/setup` | POST | Index sample data into knowledge base |
| `/docs` | GET | OpenAPI documentation |

### Example Requests

```bash
# Ask a question
curl -X POST "http://localhost:8000/api/v1/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the penalty for track limits?"}'

# Ask with conversation history
curl -X POST "http://localhost:8000/api/v1/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Can you elaborate on that?",
    "messages": [
      {"role": "user", "content": "What are track limits?"},
      {"role": "agent", "content": "Track limits define..."}
    ]
  }'

# Check setup status
curl http://localhost:8000/api/v1/setup/status
```

## ⚙️ Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_API_KEY` | Google AI API key | Yes |
| `QDRANT_URL` | Qdrant Cloud cluster URL | Yes |
| `QDRANT_API_KEY` | Qdrant Cloud API key | Yes |
| `LLM_MODEL` | Gemini model | No (default: gemini-2.0-flash) |
| `VITE_API_BASE_URL` | API URL for frontend | No (default: http://localhost:8000) |

## 📁 Project Structure

```
pitwall-ai/
├── .github/workflows/     # CI/CD pipelines
│   ├── ci.yml             # Lint, test, build
│   ├── deploy.yml         # Deploy to Cloud Run
│   └── infrastructure.yml # Terraform plan/apply
├── src/
│   ├── core/              # Domain logic (hexagonal core)
│   │   ├── domain/        # Models, exceptions, utilities
│   │   ├── ports/         # Abstract interfaces
│   │   └── services/      # AgentService, RetrievalService
│   ├── adapters/          # External integrations
│   │   ├── inbound/       # API (FastAPI), CLI (Typer)
│   │   └── outbound/      # LLM, Vector Store, Data Sources
│   └── config/            # Settings and logging
├── frontend/              # React + Vite frontend
│   ├── src/
│   │   ├── components/    # ChatInterface, Navbar
│   │   ├── services/      # API client
│   │   └── App.tsx        # Main application
│   └── public/            # Static assets (logos, bg-track.png)
├── infra/terraform/       # GCP infrastructure as code
├── tests/                 # Unit + integration tests
└── Dockerfile             # Production container
```

## 🚢 Deployment

### Automated Deployment (CI/CD)

Push to `main` branch triggers automatic deployment:
1. **CI** - Lint, tests, Docker build verification
2. **Deploy** - Build, verify container, push to Artifact Registry, deploy to Cloud Run

### Manual Deployment

```bash
cd infra/terraform

# Initialize and apply
terraform init
terraform apply -var="project_id=your-project"

# Set Google API key
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

## 🧪 Development

```bash
# Run all tests
poetry run pytest tests/ -v

# Run unit tests only
poetry run pytest tests/ -m unit -v

# Lint Python code
poetry run ruff check src/ tests/

# Auto-fix lint issues
poetry run ruff check src/ tests/ --fix

# Run frontend in dev mode
cd frontend && npm run dev
```

## 📖 Documentation

- [Developer Guide](DEVELOPER.md) - Architecture, components, and development workflow
- [Security Policy](SECURITY.md) - Security guidelines and reporting
- [Infrastructure](infra/terraform/README.md) - Terraform configuration details

## 📄 License

This project is licensed under the terms of the GNU General Public License v3.0. See [LICENSE](LICENSE) for details.
