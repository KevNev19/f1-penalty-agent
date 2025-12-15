#!/bin/bash
# F1 Penalty Agent - Setup Script for macOS/Linux
# This script checks prerequisites and sets up the development environment

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           F1 Penalty Agent - System Setup                    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Track what's installed and missing
MISSING=()
INSTALLED=()

# Function to check if a command exists
check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to get version of a command
get_version() {
    $1 --version 2>/dev/null | head -n 1 || echo "unknown"
}

echo -e "${BLUE}Checking prerequisites...${NC}"
echo ""

# Check Python
echo -n "Python 3.12+: "
if check_command python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)
    if [[ "$PYTHON_MAJOR" -ge 3 && "$PYTHON_MINOR" -ge 12 ]]; then
        echo -e "${GREEN}✓ Installed (${PYTHON_VERSION})${NC}"
        INSTALLED+=("Python $PYTHON_VERSION")
    else
        echo -e "${YELLOW}⚠ Found Python $PYTHON_VERSION but 3.12+ required${NC}"
        MISSING+=("Python 3.12+ (current: $PYTHON_VERSION)")
    fi
else
    echo -e "${RED}✗ Not found${NC}"
    MISSING+=("Python 3.12+")
fi

# Check Poetry
echo -n "Poetry: "
if check_command poetry; then
    POETRY_VERSION=$(poetry --version 2>&1 | cut -d' ' -f3)
    echo -e "${GREEN}✓ Installed (${POETRY_VERSION})${NC}"
    INSTALLED+=("Poetry $POETRY_VERSION")
else
    echo -e "${RED}✗ Not found${NC}"
    MISSING+=("Poetry")
fi

# Check Docker
echo -n "Docker: "
if check_command docker; then
    if docker info &> /dev/null; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | tr -d ',')
        echo -e "${GREEN}✓ Running (${DOCKER_VERSION})${NC}"
        INSTALLED+=("Docker $DOCKER_VERSION")
    else
        echo -e "${YELLOW}⚠ Installed but not running${NC}"
        MISSING+=("Docker (installed but not running)")
    fi
else
    echo -e "${RED}✗ Not found${NC}"
    MISSING+=("Docker Desktop")
fi

# Check kubectl
echo -n "kubectl: "
if check_command kubectl; then
    KUBECTL_VERSION=$(kubectl version --client --short 2>/dev/null | cut -d':' -f2 | tr -d ' ' || kubectl version --client 2>&1 | head -1)
    echo -e "${GREEN}✓ Installed${NC}"
    INSTALLED+=("kubectl")
else
    echo -e "${RED}✗ Not found${NC}"
    MISSING+=("kubectl")
fi

# Check Kubernetes
echo -n "Kubernetes: "
if kubectl cluster-info &> /dev/null; then
    echo -e "${GREEN}✓ Running${NC}"
    INSTALLED+=("Kubernetes cluster")
else
    echo -e "${YELLOW}⚠ Not running (enable in Docker Desktop)${NC}"
    MISSING+=("Kubernetes (enable in Docker Desktop)")
fi

# Check Git
echo -n "Git: "
if check_command git; then
    GIT_VERSION=$(git --version | cut -d' ' -f3)
    echo -e "${GREEN}✓ Installed (${GIT_VERSION})${NC}"
    INSTALLED+=("Git $GIT_VERSION")
else
    echo -e "${RED}✗ Not found${NC}"
    MISSING+=("Git")
fi

echo ""

# Summary
if [ ${#MISSING[@]} -eq 0 ]; then
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  All prerequisites are installed!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
else
    echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  Missing prerequisites:${NC}"
    echo -e "${YELLOW}════════════════════════════════════════════════════════════════${NC}"
    for item in "${MISSING[@]}"; do
        echo -e "  ${RED}• $item${NC}"
    done
    echo ""
    echo -e "${BLUE}Installation commands:${NC}"
    echo ""
    
    for item in "${MISSING[@]}"; do
        case "$item" in
            *Python*)
                echo "  # Install Python 3.12+"
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    echo "  brew install python@3.12"
                else
                    echo "  sudo apt install python3.12  # Debian/Ubuntu"
                    echo "  # or: sudo dnf install python3.12  # Fedora"
                fi
                echo ""
                ;;
            *Poetry*)
                echo "  # Install Poetry"
                echo "  curl -sSL https://install.python-poetry.org | python3 -"
                echo ""
                ;;
            *Docker*)
                echo "  # Install Docker Desktop"
                echo "  https://www.docker.com/products/docker-desktop"
                echo ""
                ;;
            *kubectl*)
                echo "  # Install kubectl (usually comes with Docker Desktop)"
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    echo "  brew install kubectl"
                else
                    echo "  # kubectl is included with Docker Desktop"
                fi
                echo ""
                ;;
            *Git*)
                echo "  # Install Git"
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    echo "  xcode-select --install  # or: brew install git"
                else
                    echo "  sudo apt install git"
                fi
                echo ""
                ;;
        esac
    done
    
    echo -e "${YELLOW}Please install missing prerequisites and run this script again.${NC}"
    exit 1
fi

echo ""

# Setup environment
echo -e "${BLUE}Setting up environment...${NC}"
echo ""

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env from .env.example${NC}"
        echo -e "${YELLOW}  → Edit .env and add your GOOGLE_API_KEY${NC}"
    else
        echo -e "${YELLOW}⚠ .env.example not found, skipping .env creation${NC}"
    fi
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

# Install Python dependencies
echo ""
echo -e "${BLUE}Installing Python dependencies...${NC}"
poetry install --extras dev
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Check for API key
echo ""
if grep -q "GOOGLE_API_KEY=your" .env 2>/dev/null || grep -q "GOOGLE_API_KEY=$" .env 2>/dev/null; then
    echo -e "${YELLOW}⚠ GOOGLE_API_KEY not set in .env${NC}"
    echo -e "  Get a free key at: ${BLUE}https://aistudio.google.com/${NC}"
else
    echo -e "${GREEN}✓ GOOGLE_API_KEY appears to be configured${NC}"
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Setup complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "  1. Ensure GOOGLE_API_KEY is set in .env"
echo ""
echo "  2. Deploy ChromaDB to Kubernetes:"
echo "     python scripts/setup_infra.py"
echo ""
echo "  3. Port-forward ChromaDB (in a separate terminal):"
echo "     kubectl port-forward -n f1-agent svc/chromadb 8000:8000"
echo ""
echo "  4. Set up knowledge base:"
echo "     poetry run f1agent setup --chroma-host localhost"
echo ""
echo "  5. Start chatting:"
echo "     poetry run f1agent chat"
echo ""
