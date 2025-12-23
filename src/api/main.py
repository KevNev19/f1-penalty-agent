"""FastAPI application for F1 Penalty Agent API."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import chat, health, setup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="F1 Penalty Agent API",
    description=(
        "AI-powered API for understanding F1 penalties and FIA regulations. "
        "Uses RAG with official FIA documents and race data."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",          # Local dev
        "http://localhost:5173",          # Vite dev server
        "https://*.web.app",              # Firebase hosting
        "https://*.firebaseapp.com",      # Firebase hosting alt
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(setup.router)


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    logger.info("F1 Penalty Agent API starting up...")
    logger.info("API docs available at /docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    logger.info("F1 Penalty Agent API shutting down...")


# Export for uvicorn
__all__ = ["app"]
