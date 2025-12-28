"""Setup endpoints for data indexing and management."""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...common.utils import chunk_text, normalize_text
from ..deps import get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["setup"])


class SetupRequest(BaseModel):
    """Request model for setup endpoint."""

    reset: bool = False
    limit: int = 0  # 0 means all data
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
        limit: Number of races to limit data to (0 = all).
        season: F1 season year.

    Returns:
        Dict with counts of indexed documents.
    """
    from ...data.fastf1_loader import FastF1Loader
    from ...data.fia_scraper import FIAScraper
    from ...data.jolpica_client import JolpicaClient
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
        # Apply limit: 0 means all, otherwise limit*2 regulations
        regs_to_process = regulations if limit == 0 else regulations[: limit * 2]

        reg_docs = []
        for reg in regs_to_process:
            scraper.download_document(reg)
            scraper.extract_text(reg)
            if reg.text_content:
                # Normalize and chunk for better search
                clean_text = normalize_text(reg.text_content)
                chunks = chunk_text(clean_text, chunk_size=1500, chunk_overlap=200)
                for i, chunk in enumerate(chunks):
                    reg_docs.append(
                        Document(
                            doc_id=f"reg-{hash(reg.url) % 10000}-{i}",
                            content=chunk,
                            metadata={
                                "source": normalize_text(reg.title),
                                "type": "regulation",
                                "url": reg.url,
                                "season": season,
                                "chunk_index": i,
                                "total_chunks": len(chunks),
                            },
                        )
                    )

        if reg_docs:
            vector_store.add_documents(reg_docs, collection_name="regulations")
            counts["regulations"] = len(reg_docs)
            logger.info(f"Indexed {len(reg_docs)} regulation chunks")
    except Exception as e:
        logger.warning(f"Failed to scrape regulations: {e}")

    # --- 2. Index Stewards Decisions ---
    logger.info(f"Scraping stewards decisions for {season}...")
    try:
        decisions = scraper.scrape_stewards_decisions(season)
        # Apply limit: 0 means all, otherwise limit*5 decisions
        decs_to_process = decisions if limit == 0 else decisions[: limit * 5]

        dec_docs = []
        for dec in decs_to_process:
            scraper.download_document(dec)
            scraper.extract_text(dec)
            if dec.text_content:
                # Normalize and chunk stewards decisions
                clean_text = normalize_text(dec.text_content)
                chunks = chunk_text(clean_text, chunk_size=1500, chunk_overlap=200)
                for i, chunk in enumerate(chunks):
                    dec_docs.append(
                        Document(
                            doc_id=f"dec-{hash(dec.url) % 10000}-{i}",
                            content=chunk,
                            metadata={
                                "source": normalize_text(dec.title),
                                "type": "stewards_decision",
                                "event": normalize_text(dec.event_name or ""),
                                "url": dec.url,
                                "season": season,
                                "chunk_index": i,
                            },
                        )
                    )

        if dec_docs:
            vector_store.add_documents(dec_docs, collection_name="stewards_decisions")
            counts["stewards_decisions"] = len(dec_docs)
            logger.info(f"Indexed {len(dec_docs)} stewards decision chunks")
    except Exception as e:
        logger.warning(f"Failed to scrape stewards decisions: {e}")

    # --- 3. Index Race Data (penalties from FastF1) ---
    logger.info(f"Loading race control data for {season}...")
    try:
        loader = FastF1Loader(cache_dir)
        events = loader.get_season_events(season)
        # Apply limit: 0 means all races, otherwise limit races
        events_to_process = events if limit == 0 else events[:limit]

        # Load Jolpica for driver context
        jolpica = JolpicaClient()
        drivers = jolpica.get_drivers(season)
        driver_map = {d.code: d.name for d in drivers}
        driver_map.update({str(d.number): d.name for d in drivers if d.number})

        race_docs = []
        for event in events_to_process:
            try:
                penalties = loader.get_race_control_messages(season, event, "Race")
                for penalty in penalties:
                    if penalty.category in ["Penalty", "Investigation", "Track Limits"]:
                        # Resolve driver name using Jolpica data
                        driver_name = penalty.driver
                        if driver_name and driver_name in driver_map:
                            driver_name = driver_map[driver_name]

                        content = normalize_text(
                            f"Race: {penalty.race_name} ({penalty.session})\n"
                            f"Driver: {driver_name or 'Unknown'}\n"
                            f"Message: {penalty.message}\n"
                            f"Category: {penalty.category}"
                        )
                        race_docs.append(
                            Document(
                                doc_id=f"race-{hash(f'{event}-{penalty.message}') % 10000}",
                                content=content,
                                metadata={
                                    "source": normalize_text(
                                        f"{penalty.race_name} {penalty.session}"
                                    ),
                                    "type": "race_control",
                                    "driver": normalize_text(driver_name or ""),
                                    "race": normalize_text(penalty.race_name),
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

    Use limit=0 (default) to index ALL available data.
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
