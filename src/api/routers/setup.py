"""Setup endpoints for data indexing and management."""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..deps import get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["setup"])


class SetupRequest(BaseModel):
    """Request model for setup endpoint."""

    reset: bool = False
    limit: int = 3
    season: int = 2025


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


def _run_setup_task(reset: bool, limit: int, season: int) -> dict:
    """Background task to index real F1 data.

    Args:
        reset: Whether to clear existing data first.
        limit: Number of races to limit data to.
        season: F1 season year.

    Returns:
        Dict with counts of indexed documents.
    """
    from ...data.fastf1_loader import FastF1Loader
    from ...data.fia_scraper import FIAScraper
    from ...rag.qdrant_store import Document

    vector_store = get_vector_store()

    if reset:
        logger.info("Resetting vector store collections...")
        vector_store.reset()

    # Set up data directories
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    cache_dir = data_dir / "fastf1_cache"
    data_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    counts = {"regulations": 0, "stewards_decisions": 0, "race_data": 0}

    # --- 1. Index FIA Regulations ---
    logger.info(f"Scraping FIA regulations for {season}...")
    try:
        scraper = FIAScraper(data_dir)
        regulations = scraper.scrape_regulations(season)

        reg_docs = []
        for reg in regulations[: limit * 2]:  # Get a few regulations
            scraper.download_document(reg)
            scraper.extract_text(reg)
            if reg.text_content:
                reg_docs.append(
                    Document(
                        doc_id=f"reg-{hash(reg.url) % 10000}",
                        content=reg.text_content[:10000],  # Limit content size
                        metadata={
                            "source": reg.title,
                            "type": "regulation",
                            "url": reg.url,
                            "season": season,
                        },
                    )
                )

        if reg_docs:
            vector_store.add_documents(reg_docs, collection_name="regulations")
            counts["regulations"] = len(reg_docs)
            logger.info(f"Indexed {len(reg_docs)} regulations")
    except Exception as e:
        logger.warning(f"Failed to scrape regulations: {e}")

    # --- 2. Index Stewards Decisions ---
    logger.info(f"Scraping stewards decisions for {season}...")
    try:
        decisions = scraper.scrape_stewards_decisions(season)

        dec_docs = []
        for dec in decisions[: limit * 5]:  # Get more decisions
            scraper.download_document(dec)
            scraper.extract_text(dec)
            if dec.text_content:
                dec_docs.append(
                    Document(
                        doc_id=f"dec-{hash(dec.url) % 10000}",
                        content=dec.text_content,
                        metadata={
                            "source": dec.title,
                            "type": "stewards_decision",
                            "event": dec.event_name,
                            "url": dec.url,
                            "season": season,
                        },
                    )
                )

        if dec_docs:
            vector_store.add_documents(dec_docs, collection_name="stewards_decisions")
            counts["stewards_decisions"] = len(dec_docs)
            logger.info(f"Indexed {len(dec_docs)} stewards decisions")
    except Exception as e:
        logger.warning(f"Failed to scrape stewards decisions: {e}")

    # --- 3. Index Race Data (penalties from FastF1) ---
    logger.info(f"Loading race control data for {season}...")
    try:
        loader = FastF1Loader(cache_dir)
        events = loader.get_season_events(season)

        race_docs = []
        for event in events[:limit]:
            try:
                penalties = loader.get_race_control_messages(season, event, "Race")
                for penalty in penalties:
                    if penalty.category in ["Penalty", "Investigation", "Track Limits"]:
                        race_docs.append(
                            Document(
                                doc_id=f"race-{hash(f'{event}-{penalty.message}') % 10000}",
                                content=f"Race: {penalty.race_name} ({penalty.session})\n"
                                f"Driver: {penalty.driver or 'Unknown'}\n"
                                f"Message: {penalty.message}\n"
                                f"Category: {penalty.category}",
                                metadata={
                                    "source": f"{penalty.race_name} {penalty.session}",
                                    "type": "race_control",
                                    "driver": penalty.driver,
                                    "race": penalty.race_name,
                                    "season": season,
                                },
                            )
                        )
            except Exception as e:
                logger.warning(f"Failed to load race data for {event}: {e}")
                continue

        if race_docs:
            vector_store.add_documents(race_docs, collection_name="race_data")
            counts["race_data"] = len(race_docs)
            logger.info(f"Indexed {len(race_docs)} race control messages")
    except Exception as e:
        logger.warning(f"Failed to load race data: {e}")

    return counts


@router.post("/setup", response_model=SetupResponse)
async def run_setup(request: SetupRequest) -> SetupResponse:
    """Index real F1 data into the knowledge base.

    This endpoint scrapes FIA regulations and stewards decisions,
    and loads race control messages from FastF1.
    Use reset=true to clear existing data before indexing.

    Args:
        request: Setup configuration options.

    Returns:
        SetupResponse with status and collection counts.
    """
    try:
        logger.info(
            f"Starting setup: season={request.season}, limit={request.limit}, reset={request.reset}"
        )

        # Run synchronously for now (could make async with BackgroundTasks)
        counts = _run_setup_task(request.reset, request.limit, request.season)

        total = sum(counts.values())

        return SetupResponse(
            status="success",
            message=f"Indexed {total} documents: {counts['regulations']} regulations, "
            f"{counts['stewards_decisions']} decisions, {counts['race_data']} race events",
            collections=counts,
        )

    except Exception as e:
        logger.exception(f"Error during setup: {e}")
        raise HTTPException(status_code=500, detail=f"Setup failed: {e}")
