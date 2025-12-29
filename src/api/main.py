"""FastAPI application for F1 Penalty Agent API."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .routers import chat, health, setup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class BOMSanitizationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle BOM and encoding issues in requests/responses."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except UnicodeEncodeError as e:
            # Catch encoding errors and return a clean JSON error
            logger.error(f"UnicodeEncodeError caught by middleware: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Encoding error occurred. Please try again."},
            )


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

# Add BOM sanitization middleware first
app.add_middleware(BOMSanitizationMiddleware)

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


@app.exception_handler(UnicodeEncodeError)
async def unicode_encode_error_handler(request: Request, exc: UnicodeEncodeError):
    """Handle UnicodeEncodeError globally."""
    logger.error(f"UnicodeEncodeError: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Text encoding error. The system encountered an encoding issue."},
    )


@app.exception_handler(UnicodeDecodeError)
async def unicode_decode_error_handler(request: Request, exc: UnicodeDecodeError):
    """Handle UnicodeDecodeError globally."""
    logger.error(f"UnicodeDecodeError: {exc}")
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid text encoding in request."},
    )


# Include routers
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(setup.router)


@app.on_event("startup")
async def startup_event():
    """Initialize resources on startup."""
    from ..common.debug import log_encoding_info

    log_encoding_info()

    logger.info("F1 Penalty Agent API starting up...")
    logger.info("API docs available at /docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on shutdown."""
    logger.info("F1 Penalty Agent API shutting down...")


# Export for uvicorn
__all__ = ["app"]
