"""Health check endpoints."""

from fastapi import APIRouter

from ..deps import get_vector_store
from ..models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Basic health check endpoint.

    Returns:
        HealthResponse with current status and version.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        vector_store="not_checked",
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness_check() -> HealthResponse:
    """Kubernetes readiness probe.

    Checks that vector store is accessible.

    Returns:
        HealthResponse with detailed status.
    """
    try:
        vector_store = get_vector_store()
        # Aggregate stats from all collections
        regs = vector_store.get_collection_stats(vector_store.REGULATIONS_COLLECTION).get(
            "count", 0
        )
        stewards = vector_store.get_collection_stats(vector_store.STEWARDS_COLLECTION).get(
            "count", 0
        )
        race = vector_store.get_collection_stats(vector_store.RACE_DATA_COLLECTION).get("count", 0)

        total = regs + stewards + race
        vs_status = f"connected ({total} docs: {regs} regs, {stewards} decisions, {race} race)"
    except Exception as e:
        vs_status = f"error: {str(e)}"

    return HealthResponse(
        status="ready",
        version="1.0.0",
        vector_store=vs_status,
    )
