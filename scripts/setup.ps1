# F1 Penalty Agent - Setup Script for Windows
# This script checks prerequisites and sets up the development environment
# Run with: .\scripts\setup.ps1

$ErrorActionPreference = "Continue"

Write-Host "================================================================" -ForegroundColor Blue
Write-Host "           F1 Penalty Agent - System Setup                     " -ForegroundColor Blue
Write-Host "================================================================" -ForegroundColor Blue
Write-Host ""

# Track what's installed and missing
$Missing = @()
$Installed = @()

# Function to check if a command exists
function Test-CommandExists {
    param([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

Write-Host "Checking prerequisites..." -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host -NoNewline "Python 3.12+: "
if (Test-CommandExists "python") {
    try {
        $pythonVersion = (python --version 2>&1) -replace "Python ", ""
        $versionParts = $pythonVersion.Split(".")
        $major = [int]$versionParts[0]
        $minor = [int]$versionParts[1]
        if ($major -ge 3 -and $minor -ge 12) {
            Write-Host "Installed ($pythonVersion)" -ForegroundColor Green
            $Installed += "Python $pythonVersion"
        }
        else {
            Write-Host "Found Python $pythonVersion but 3.12+ required" -ForegroundColor Yellow
            $Missing += "Python 3.12+ (current: $pythonVersion)"
        }
    }
    catch {
        Write-Host "Error checking version" -ForegroundColor Red
        $Missing += "Python 3.12+"
    }
}
else {
    Write-Host "Not found" -ForegroundColor Red
    $Missing += "Python 3.12+"
}

# Check Poetry
Write-Host -NoNewline "Poetry: "
$poetryPath = "$env:APPDATA\Python\Scripts\poetry.exe"
if ((Test-CommandExists "poetry") -or (Test-Path $poetryPath)) {
    Write-Host "Installed" -ForegroundColor Green
    $Installed += "Poetry"
}
else {
    Write-Host "Not found" -ForegroundColor Red
    $Missing += "Poetry"
}

# Check Docker
Write-Host -NoNewline "Docker: "
if (Test-CommandExists "docker") {
    try {
        $null = docker info 2>&1
        $dockerVersion = ((docker --version) -split " ")[2] -replace ",", ""
        Write-Host "Running ($dockerVersion)" -ForegroundColor Green
        $Installed += "Docker $dockerVersion"
    }
    catch {
        Write-Host "Installed but not running" -ForegroundColor Yellow
        $Missing += "Docker (installed but not running)"
    }
}
else {
    Write-Host "Not found" -ForegroundColor Red
    $Missing += "Docker Desktop"
}

# Check kubectl
Write-Host -NoNewline "kubectl: "
if (Test-CommandExists "kubectl") {
    Write-Host "Installed" -ForegroundColor Green
    $Installed += "kubectl"
}
else {
    Write-Host "Not found" -ForegroundColor Red
    $Missing += "kubectl"
}

# Check Kubernetes
Write-Host -NoNewline "Kubernetes: "
try {
    $null = kubectl cluster-info 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Running" -ForegroundColor Green
        $Installed += "Kubernetes cluster"
    }
    else {
        throw "Not running"
    }
}
catch {
    Write-Host "Not running (enable in Docker Desktop)" -ForegroundColor Yellow
    $Missing += "Kubernetes (enable in Docker Desktop)"
}

# Check Git
Write-Host -NoNewline "Git: "
if (Test-CommandExists "git") {
    $gitVersion = (git --version) -replace "git version ", ""
    Write-Host "Installed ($gitVersion)" -ForegroundColor Green
    $Installed += "Git $gitVersion"
}
else {
    Write-Host "Not found" -ForegroundColor Red
    $Missing += "Git"
}

Write-Host ""

# Summary
if ($Missing.Count -eq 0) {
    Write-Host "================================================================" -ForegroundColor Green
    Write-Host "  All prerequisites are installed!" -ForegroundColor Green
    Write-Host "================================================================" -ForegroundColor Green
}
else {
    Write-Host "================================================================" -ForegroundColor Yellow
    Write-Host "  Missing prerequisites:" -ForegroundColor Yellow
    Write-Host "================================================================" -ForegroundColor Yellow
    foreach ($item in $Missing) {
        Write-Host "  * $item" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Installation commands:" -ForegroundColor Cyan
    Write-Host ""
    
    foreach ($item in $Missing) {
        if ($item -like "*Python*") {
            Write-Host "  # Install Python 3.12+"
            Write-Host "  winget install Python.Python.3.12"
            Write-Host ""
        }
        if ($item -like "*Poetry*") {
            Write-Host "  # Install Poetry"
            Write-Host "  (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -"
            Write-Host ""
        }
        if ($item -like "*Docker*") {
            Write-Host "  # Install Docker Desktop"
            Write-Host "  winget install Docker.DockerDesktop"
            Write-Host ""
        }
        if ($item -like "*kubectl*") {
            Write-Host "  # kubectl is included with Docker Desktop"
            Write-Host ""
        }
        if ($item -like "*Git*") {
            Write-Host "  # Install Git"
            Write-Host "  winget install Git.Git"
            Write-Host ""
        }
    }
    
    Write-Host "Please install missing prerequisites and run this script again." -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Setup environment
Write-Host "Setting up environment..." -ForegroundColor Cyan
Write-Host ""

# Create .env if it doesn't exist
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example" -ForegroundColor Green
        Write-Host "  Edit .env and add your GOOGLE_API_KEY" -ForegroundColor Yellow
    }
    else {
        Write-Host ".env.example not found, skipping .env creation" -ForegroundColor Yellow
    }
}
else {
    Write-Host ".env already exists" -ForegroundColor Green
}

# Install Python dependencies
Write-Host ""
Write-Host "Installing Python dependencies..." -ForegroundColor Cyan

# Refresh PATH to include Poetry
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User") + ";$env:APPDATA\Python\Scripts"

try {
    $poetryExe = "$env:APPDATA\Python\Scripts\poetry.exe"
    if (Test-Path $poetryExe) {
        & $poetryExe install --extras dev
    }
    elseif (Test-CommandExists "poetry") {
        poetry install --extras dev
    }
    else {
        throw "Poetry not found"
    }
    Write-Host "Dependencies installed" -ForegroundColor Green
}
catch {
    Write-Host "Failed to install dependencies: $_" -ForegroundColor Red
}

# Check for API key
Write-Host ""
$envContent = Get-Content ".env" -Raw -ErrorAction SilentlyContinue
if ($envContent -match "GOOGLE_API_KEY=your|GOOGLE_API_KEY=\s*$") {
    Write-Host "GOOGLE_API_KEY not set in .env" -ForegroundColor Yellow
    Write-Host "  Get a free key at: https://aistudio.google.com/"
}
else {
    Write-Host "GOOGLE_API_KEY appears to be configured" -ForegroundColor Green
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Setup complete!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Ensure GOOGLE_API_KEY is set in .env"
Write-Host ""
Write-Host "  2. Deploy ChromaDB to Kubernetes:"
Write-Host "     python scripts\setup_infra.py"
Write-Host ""
Write-Host "  3. Port-forward ChromaDB (in a separate terminal):"
Write-Host "     kubectl port-forward -n f1-agent svc/chromadb 8000:8000"
Write-Host ""
Write-Host "  4. Set up knowledge base:"
Write-Host '     $env:CHROMA_HOST="localhost"; poetry run f1agent setup --chroma-host localhost'
Write-Host ""
Write-Host "  5. Start chatting:"
Write-Host '     $env:CHROMA_HOST="localhost"; poetry run f1agent chat'
Write-Host ""
