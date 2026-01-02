"""Setup endpoints for data indexing and management."""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .....core.domain.utils import chunk_text, normalize_text
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
    from .....adapters.outbound.data_sources.fastf1_adapter import FastF1Adapter as FastF1Loader
    from .....adapters.outbound.data_sources.fia_adapter import FIAAdapter as FIAScraper
    from .....adapters.outbound.data_sources.jolpica_adapter import JolpicaAdapter as JolpicaClient
    from .....core.domain import Document

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


# ==============================================================================
# SSE Streaming Setup Endpoint
# ==============================================================================


class SetupProgressEvent(BaseModel):
    """Progress event for SSE streaming."""

    event_type: str  # "start", "phase", "progress", "complete", "error"
    data_type: str | None = None  # "regulations", "stewards_decisions", "race_data"
    phase: str | None = None  # "discovery", "download", "index"
    current: int = 0
    total: int = 0
    item: str | None = None
    message: str | None = None
    totals: dict[str, int] | None = None


async def _generate_setup_events(reset: bool, limit: int, season: int):
    """Generator that yields SSE events during setup.

    Args:
        reset: Whether to clear existing data first.
        limit: Number of races to limit data to (0 = all).
        season: F1 season year.

    Yields:
        SSE formatted event strings.
    """
    import asyncio
    import hashlib
    import json

    from .....adapters.outbound.data_sources.fia_adapter import FIAAdapter as FIAScraper
    from .....config.settings import settings
    from .....core.domain import Document
    from .....core.domain.utils import chunk_text, normalize_text

    def make_event(event_type: str, **kwargs) -> str:
        """Format an SSE event."""
        data = {"event_type": event_type, **kwargs}
        return f"data: {json.dumps(data)}\n\n"

    yield make_event("start", message=f"Starting setup for {season} season")
    await asyncio.sleep(0.1)

    vector_store = get_vector_store()
    config_hash = settings.get_config_hash()

    if reset:
        yield make_event("phase", phase="reset", message="Resetting collections...")
        await asyncio.sleep(0.1)
        vector_store.reset()

    data_dir = Path(settings.data_dir)
    cache_dir = data_dir / "fastf1_cache"
    data_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    counts = {"regulations": 0, "stewards_decisions": 0, "race_data": 0}

    # --- 1. Regulations ---
    yield make_event(
        "phase", data_type="regulations", phase="discovery", message="Scanning regulations..."
    )
    await asyncio.sleep(0.1)

    try:
        scraper = FIAScraper(data_dir)
        regulations = scraper.scrape_regulations(season)
        regs_to_process = regulations if limit == 0 else regulations[: limit * 2]

        yield make_event(
            "phase",
            data_type="regulations",
            phase="discovery",
            total=len(regs_to_process),
            message=f"Found {len(regs_to_process)} regulations",
        )
        await asyncio.sleep(0.1)

        yield make_event(
            "phase", data_type="regulations", phase="download", total=len(regs_to_process)
        )

        reg_docs = []
        for i, reg in enumerate(regs_to_process):
            if vector_store.document_exists("regulations", reg.url, config_hash):
                yield make_event(
                    "progress",
                    data_type="regulations",
                    phase="download",
                    current=i + 1,
                    total=len(regs_to_process),
                    item=f"Skipped: {reg.title[:40]}",
                )
            else:
                yield make_event(
                    "progress",
                    data_type="regulations",
                    phase="download",
                    current=i + 1,
                    total=len(regs_to_process),
                    item=reg.title[:50],
                )

                try:
                    scraper.download_document(reg)
                    scraper.extract_text(reg)
                    if reg.text_content:
                        clean_text = normalize_text(reg.text_content)
                        chunks = chunk_text(
                            clean_text,
                            chunk_size=settings.chunk_size,
                            chunk_overlap=settings.chunk_overlap,
                        )
                        doc_hash = hashlib.md5(reg.url.encode()).hexdigest()[:10]
                        for j, chunk in enumerate(chunks):
                            reg_docs.append(
                                Document(
                                    doc_id=f"reg-{doc_hash}-{j}",
                                    content=chunk,
                                    metadata={
                                        "source": normalize_text(reg.title),
                                        "type": "regulation",
                                        "url": reg.url,
                                        "season": season,
                                        "chunk_index": j,
                                        "total_chunks": len(chunks),
                                        "config_hash": config_hash,
                                    },
                                )
                            )
                except Exception as e:
                    logger.warning(f"Failed to process {reg.title}: {e}")

            # Yield control periodically
            if i % 3 == 0:
                await asyncio.sleep(0.05)

        if reg_docs:
            yield make_event(
                "phase",
                data_type="regulations",
                phase="index",
                total=len(reg_docs),
                message="Indexing...",
            )
            await asyncio.sleep(0.1)
            vector_store.add_documents(reg_docs, collection_name="regulations")
            counts["regulations"] = len(reg_docs)
            yield make_event(
                "phase",
                data_type="regulations",
                phase="complete",
                message=f"+{len(reg_docs)} documents",
            )

    except Exception as e:
        yield make_event("error", data_type="regulations", message=str(e))

    # --- 2. Stewards Decisions ---
    yield make_event(
        "phase",
        data_type="stewards_decisions",
        phase="discovery",
        message="Scanning stewards decisions...",
    )
    await asyncio.sleep(0.1)

    try:
        decisions = scraper.scrape_stewards_decisions(season)
        decs_to_process = decisions if limit == 0 else decisions[: limit * 5]

        yield make_event(
            "phase",
            data_type="stewards_decisions",
            phase="discovery",
            total=len(decs_to_process),
            message=f"Found {len(decs_to_process)} decisions",
        )
        await asyncio.sleep(0.1)

        yield make_event(
            "phase", data_type="stewards_decisions", phase="download", total=len(decs_to_process)
        )

        dec_docs = []
        for i, dec in enumerate(decs_to_process):
            if vector_store.document_exists("stewards_decisions", dec.url, config_hash):
                yield make_event(
                    "progress",
                    data_type="stewards_decisions",
                    phase="download",
                    current=i + 1,
                    total=len(decs_to_process),
                    item=f"Skipped: {dec.title[:40]}",
                )
            else:
                yield make_event(
                    "progress",
                    data_type="stewards_decisions",
                    phase="download",
                    current=i + 1,
                    total=len(decs_to_process),
                    item=dec.title[:50],
                )
                try:
                    scraper.download_document(dec)
                    scraper.extract_text(dec)
                    if dec.text_content:
                        clean_text = normalize_text(dec.text_content)
                        chunks = chunk_text(
                            clean_text,
                            chunk_size=settings.chunk_size,
                            chunk_overlap=settings.chunk_overlap,
                        )
                        doc_hash = hashlib.md5(dec.url.encode()).hexdigest()[:10]
                        for j, chunk in enumerate(chunks):
                            dec_docs.append(
                                Document(
                                    doc_id=f"dec-{doc_hash}-{j}",
                                    content=chunk,
                                    metadata={
                                        "source": normalize_text(dec.title),
                                        "type": "stewards_decision",
                                        "event": normalize_text(dec.event_name or ""),
                                        "url": dec.url,
                                        "season": season,
                                        "chunk_index": j,
                                        "config_hash": config_hash,
                                    },
                                )
                            )
                except Exception as e:
                    logger.warning(f"Failed to process {dec.title}: {e}")

            if i % 5 == 0:
                await asyncio.sleep(0.05)

        if dec_docs:
            yield make_event(
                "phase",
                data_type="stewards_decisions",
                phase="index",
                total=len(dec_docs),
                message="Indexing...",
            )
            await asyncio.sleep(0.1)
            vector_store.add_documents(dec_docs, collection_name="stewards_decisions")
            counts["stewards_decisions"] = len(dec_docs)
            yield make_event(
                "phase",
                data_type="stewards_decisions",
                phase="complete",
                message=f"+{len(dec_docs)} documents",
            )

    except Exception as e:
        yield make_event("error", data_type="stewards_decisions", message=str(e))

    # --- 3. Race Data ---
    yield make_event(
        "phase", data_type="race_data", phase="discovery", message="Scanning race events..."
    )
    await asyncio.sleep(0.1)

    try:
        from .....adapters.outbound.data_sources.fastf1_adapter import FastF1Adapter as FastF1Loader
        from .....adapters.outbound.data_sources.jolpica_adapter import (
            JolpicaAdapter as JolpicaClient,
        )

        loader = FastF1Loader(cache_dir)
        events = loader.get_season_events(season)
        events_to_process = events if limit == 0 else events[:limit]

        yield make_event(
            "phase",
            data_type="race_data",
            phase="discovery",
            total=len(events_to_process),
            message=f"Found {len(events_to_process)} races",
        )

        jolpica = JolpicaClient()
        drivers = jolpica.get_drivers(season)
        driver_map = {d.code: d.name for d in drivers}
        driver_map.update({str(d.number): d.name for d in drivers if d.number})
        team_map = jolpica.get_driver_teams_map(season)

        yield make_event(
            "phase", data_type="race_data", phase="download", total=len(events_to_process)
        )

        race_docs = []
        for i, event in enumerate(events_to_process):
            yield make_event(
                "progress",
                data_type="race_data",
                phase="download",
                current=i + 1,
                total=len(events_to_process),
                item=event,
            )
            try:
                penalties = loader.get_race_control_messages(season, event, "Race")
                for penalty in penalties:
                    if penalty.category in ["Penalty", "Investigation", "Track Limits"]:
                        driver_name = penalty.driver
                        if driver_name and driver_name in driver_map:
                            driver_name = driver_map[driver_name]
                        team_name = penalty.team or "Unknown"
                        if team_name == "Unknown" and driver_name in team_map:
                            team_name = team_map[driver_name]

                        msg_content = f"{event}-{penalty.session}-{penalty.message}"
                        msg_hash = hashlib.md5(msg_content.encode()).hexdigest()[:10]
                        synthetic_url = f"fastf1://{season}/{event}/{penalty.session}/{msg_hash}"

                        if vector_store.document_exists("race_data", synthetic_url, config_hash):
                            continue

                        content = normalize_text(
                            f"Race: {penalty.race_name} ({penalty.session})\n"
                            f"Driver: {driver_name or 'Unknown'}\n"
                            f"Team: {team_name}\n"
                            f"Message: {penalty.message}\n"
                            f"Category: {penalty.category}"
                        )
                        race_docs.append(
                            Document(
                                doc_id=f"race-{msg_hash}",
                                content=content,
                                metadata={
                                    "source": normalize_text(
                                        f"{penalty.race_name} {penalty.session}"
                                    ),
                                    "type": "race_control",
                                    "driver": normalize_text(driver_name or ""),
                                    "team": normalize_text(team_name),
                                    "race": normalize_text(penalty.race_name),
                                    "season": season,
                                    "url": synthetic_url,
                                    "config_hash": config_hash,
                                },
                            )
                        )
            except Exception as e:
                logger.warning(f"Failed to load race data for {event}: {e}")

            await asyncio.sleep(0.05)

        if race_docs:
            yield make_event(
                "phase",
                data_type="race_data",
                phase="index",
                total=len(race_docs),
                message="Indexing...",
            )
            await asyncio.sleep(0.1)
            vector_store.add_documents(race_docs, collection_name="race_data")
            counts["race_data"] = len(race_docs)
            yield make_event(
                "phase",
                data_type="race_data",
                phase="complete",
                message=f"+{len(race_docs)} documents",
            )

    except Exception as e:
        yield make_event("error", data_type="race_data", message=str(e))

    # Final summary
    total = sum(counts.values())
    yield make_event(
        "complete", totals=counts, message=f"Setup complete! Indexed {total} documents"
    )


@router.post("/admin/setup/stream")
async def run_setup_stream(request: SetupRequest):
    """Run setup with SSE streaming for real-time progress.

    This endpoint streams progress events as Server-Sent Events (SSE).
    Connect with EventSource to receive real-time updates.

    Args:
        request: Setup configuration options.

    Returns:
        StreamingResponse with SSE events.
    """
    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        _generate_setup_events(request.reset, request.limit, request.season),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
