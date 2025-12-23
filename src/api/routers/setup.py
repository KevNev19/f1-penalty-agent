"""Setup endpoints for data indexing and management."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..deps import get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["setup"])


class SetupRequest(BaseModel):
    """Request model for setup endpoint."""

    reset: bool = False
    limit: int = 3


class SetupResponse(BaseModel):
    """Response model for setup endpoint."""

    status: str
    message: str
    collections: dict[str, int] | None = None


class SetupStatusResponse(BaseModel):
    """Response model for setup status."""

    status: str
    is_populated: bool
    collections: dict[str, int]


@router.get("/setup/status", response_model=SetupStatusResponse)
async def get_setup_status() -> SetupStatusResponse:
    """Check if the knowledge base has been set up with data.

    Returns:
        SetupStatusResponse with population status and collection counts.
    """
    try:
        vector_store = get_vector_store()
        collections = {}
        total = 0

        for collection in ["regulations", "stewards_decisions", "race_data"]:
            stats = vector_store.get_collection_stats(collection)
            count = stats.get("count", 0)
            collections[collection] = count
            total += count

        return SetupStatusResponse(
            status="ok",
            is_populated=total > 0,
            collections=collections,
        )
    except Exception as e:
        logger.exception(f"Error checking setup status: {e}")
        raise HTTPException(status_code=500, detail=f"Error checking status: {e}")


@router.post("/setup", response_model=SetupResponse)
async def run_setup(request: SetupRequest) -> SetupResponse:
    """Index sample data into the knowledge base.

    This endpoint indexes sample F1 regulations and stewards decisions.
    Use reset=true to clear existing data before indexing.

    Args:
        request: Setup configuration options.

    Returns:
        SetupResponse with status and collection counts.
    """
    from ...rag.qdrant_store import Document
    from ..deps import get_vector_store

    try:
        vector_store = get_vector_store()

        if request.reset:
            logger.info("Resetting vector store collections...")
            vector_store.reset()

        # Index sample regulations
        logger.info("Indexing sample regulations...")
        regulations = [
            Document(
                doc_id="reg-1",
                content="Track limits are defined by the white lines at the edge of the circuit. Drivers who exceed track limits may have their lap times deleted or receive penalties.",
                metadata={"source": "FIA Sporting Regulations", "type": "regulation"},
            ),
            Document(
                doc_id="reg-2",
                content="A 5-second time penalty is typically applied for minor infractions such as causing a collision, exceeding track limits repeatedly, or unsafe driving.",
                metadata={"source": "FIA Sporting Regulations", "type": "regulation"},
            ),
            Document(
                doc_id="reg-3",
                content="A 10-second time penalty is applied for more serious infractions or repeat offenses during a Grand Prix.",
                metadata={"source": "FIA Sporting Regulations", "type": "regulation"},
            ),
        ]
        vector_store.add_documents(regulations, collection_name="regulations")

        # Index sample stewards decisions
        logger.info("Indexing sample stewards decisions...")
        decisions = [
            Document(
                doc_id="dec-1",
                content="Driver received a 5-second time penalty for causing a collision at Turn 1. The stewards determined the driver was predominantly at fault for the contact.",
                metadata={"source": "Stewards Decision", "type": "decision"},
            ),
            Document(
                doc_id="dec-2",
                content="Driver received a 10-second time penalty for leaving the track and gaining a lasting advantage. The driver failed to give back the position gained.",
                metadata={"source": "Stewards Decision", "type": "decision"},
            ),
        ]
        vector_store.add_documents(decisions, collection_name="stewards_decisions")

        # Get final counts
        collections = {}
        for collection in ["regulations", "stewards_decisions", "race_data"]:
            stats = vector_store.get_collection_stats(collection)
            collections[collection] = stats.get("count", 0)

        return SetupResponse(
            status="success",
            message=f"Indexed {len(regulations)} regulations and {len(decisions)} stewards decisions",
            collections=collections,
        )

    except Exception as e:
        logger.exception(f"Error during setup: {e}")
        raise HTTPException(status_code=500, detail=f"Setup failed: {e}")
