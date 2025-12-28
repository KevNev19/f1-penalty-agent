# Multi-stage Dockerfile for F1 Penalty Agent API
# Stage 1: Builder - install dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build tools
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==2.2.1 && poetry self add poetry-plugin-export

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Export dependencies to requirements.txt, excluding hashes to allow modified wheel selection
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes --only main \
    && sed -i '/nvidia-/d' requirements.txt \
    && sed -i '/triton/d' requirements.txt

# Install dependencies using pinned CPU-only index for PyTorch
# We keep PyPI as extra-index for all other packages
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    --index-url https://download.pytorch.org/whl/cpu \
    --extra-index-url https://pypi.org/simple

# Copy source code
COPY src/ ./src/


# Stage 2: Runtime - minimal image
FROM python:3.12-slim AS runtime

WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Install curl for healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --from=builder /app/src ./src

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set encoding to UTF-8 to prevent ASCII errors with BOM
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
