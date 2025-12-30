"""FastAPI application for F1 Penalty Agent API."""

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ....core.domain.exceptions import F1AgentError
from ...common.exception_handler import (
    format_exception_json,
    get_http_status_code,
    log_exception,
)
from .routers import chat, health, setup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Determine if we're in debug mode (shows full stack traces)
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"

# Create FastAPI app
app = FastAPI(
    title="PitWallAI API",
    description=(
        "AI-powered official Pit Wall assistant for Formula 1. "
        "Explains penalties and FIA regulations using RAG with official documents."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local dev
        "http://localhost:5173",  # Vite dev server
        "https://*.web.app",  # Firebase hosting
        "https://*.firebaseapp.com",  # Firebase hosting alt
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(setup.router)


# =============================================================================
# Global Exception Handlers
# =============================================================================


@app.exception_handler(F1AgentError)
async def f1_agent_error_handler(request: Request, exc: F1AgentError) -> JSONResponse:
    """Handle all F1AgentError exceptions with structured JSON response.

    Args:
        request: The incoming request.
        exc: The F1AgentError exception.

    Returns:
        JSONResponse with structured error details.
    """
    log_exception(exc, extra_context={"path": str(request.url.path), "method": request.method})

    return JSONResponse(
        status_code=get_http_status_code(exc),
        content=exc.to_dict(include_trace=DEBUG_MODE),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle all unhandled exceptions with structured JSON response.

    Args:
        request: The incoming request.
        exc: The unhandled exception.

    Returns:
        JSONResponse with structured error details.
    """
    log_exception(exc, extra_context={"path": str(request.url.path), "method": request.method})

    error_data = format_exception_json(exc, include_trace=DEBUG_MODE)

    return JSONResponse(
        status_code=get_http_status_code(exc),
        content=error_data,
    )


# =============================================================================
# Lifecycle Events
# =============================================================================


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    from ...common.debug import log_encoding_info

    log_encoding_info()

    logger.info("F1 Penalty Agent API starting up...")
    logger.info("API docs available at /docs")
    logger.info("Debug mode: %s", "ENABLED" if DEBUG_MODE else "DISABLED")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    logger.info("F1 Penalty Agent API shutting down...")


# Export for uvicorn
__all__ = ["app"]
