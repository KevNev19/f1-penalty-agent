"""CLI interface for the F1 Penalty Agent."""

import hashlib
import json
import os
from typing import Any

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from ....config.settings import settings
from ....core.domain.utils import chunk_text, normalize_text
from ...common.exception_handler import format_exception_json

app = typer.Typer(
    name="pitwall",
    help="PitWallAI - Official F1 strategic penalty and regulation assistant",
    add_completion=False,
)

# Fix Windows encoding issues with emojis
console = Console(force_terminal=True, legacy_windows=False)

# Determine if we're in debug mode (shows full stack traces)
DEBUG_MODE = os.getenv("DEBUG", "false").lower() == "true"


def handle_cli_error(exc: Exception) -> None:
    """Handle and display errors in CLI with structured format.

    In debug mode, shows full JSON error details.
    In normal mode, shows a user-friendly message with error code.

    Args:
        exc: The exception to handle.
    """
    error_data = format_exception_json(exc, include_trace=DEBUG_MODE)

    if DEBUG_MODE:
        # Full JSON output for debugging
        console.print(
            Panel(
                json.dumps(error_data, indent=2),
                title="[bold red]Error Details[/]",
                border_style="red",
            )
        )
    else:
        # User-friendly message
        error_type = error_data["error"]["type"]
        error_msg = error_data["error"]["message"]
        error_code = error_data["error"].get("code", "UNKNOWN")
        location = error_data.get("location", {})

        console.print(f"\n[red]Error [{error_code}]:[/] {error_msg}")
        console.print(f"[dim]Type: {error_type}[/]")

        if location:
            loc_str = f"{location.get('file', '?')}:{location.get('line', '?')} in {location.get('method', '?')}"
            console.print(f"[dim]Location: {loc_str}[/]")

        console.print("[dim]Set DEBUG=true for full details[/]")


def get_agent():
    """Get or create the F1 agent instance."""
    from ....adapters.outbound.llm.gemini_adapter import GeminiAdapter as GeminiClient
    from ....adapters.outbound.sqlite_adapter import SQLiteAdapter
    from ....adapters.outbound.vector_store.qdrant_adapter import QdrantAdapter as QdrantVectorStore
    from ....config.settings import settings
    from ....core.services.agent_service import AgentService as F1Agent
    from ....core.services.retrieval_service import RetrievalService as F1Retriever

    settings.ensure_directories()

    if not settings.google_api_key:
        console.print(
            "[red]Error:[/] Google API key not set.\n"
            "Get a free key at https://aistudio.google.com/ and set GOOGLE_API_KEY in .env"
        )
        raise typer.Exit(1)

    if not settings.qdrant_url or not settings.qdrant_api_key:
        console.print(
            "[red]Error:[/] Qdrant credentials not set.\n"
            "Get a free account at https://cloud.qdrant.io/ and set QDRANT_URL and QDRANT_API_KEY in .env"
        )
        raise typer.Exit(1)

    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        embedding_api_key=settings.google_api_key,
    )
    retriever = F1Retriever(vector_store, use_reranker=False)  # Disable for CLI (slow startup)
    llm = GeminiClient(settings.google_api_key, settings.llm_model)

    sql_adapter = SQLiteAdapter()
    return F1Agent(llm, retriever, sql_adapter)


@app.command()
def chat() -> None:
    """Start an interactive chat session with the F1 agent."""
    console.print(
        Panel.fit(
            "[bold red]🏎️ PitWallAI[/]\n"
            "[dim]Official F1 strategic penalty and regulation assistant[/]\n\n"
            "Examples:\n"
            "• Why did Verstappen get a penalty in Austria?\n"
            "• What's the rule for track limits?\n"
            "• How are unsafe pit releases penalized?\n\n"
            "[dim]Type 'quit' or 'exit' to leave[/]",
            title="Welcome to PitWallAI",
            border_style="red",
        )
    )

    try:
        agent = get_agent()
    except Exception as exc:
        handle_cli_error(exc)
        raise typer.Exit(1)

    while True:
        try:
            query = Prompt.ask("\n[bold cyan]You[/]")

            if query.lower() in ("quit", "exit", "q"):
                console.print("[dim]Goodbye! 🏁[/]")
                break

            if not query.strip():
                continue

            with console.status("[bold green]Thinking...[/]"):
                response = agent.ask(query)

            console.print()
            console.print(
                Panel(
                    Markdown(response.answer),
                    title="[bold red]F1 Agent[/]",
                    border_style="red",
                )
            )

            if response.sources_used:
                console.print("[dim]Sources used:[/]")
                for source in response.sources_used[:3]:
                    console.print(f"  [dim]{source}[/]")

        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye! 🏁[/]")
            break
        except Exception as exc:
            handle_cli_error(exc)


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question about F1 penalties or rules"),
) -> None:
    """Ask a single question and get an answer."""
    try:
        agent = get_agent()
    except Exception as exc:
        handle_cli_error(exc)
        raise typer.Exit(1)

    with console.status("[bold green]Thinking...[/]"):
        response = agent.ask(question)

    console.print(Markdown(response.answer))

    if response.sources_used:
        console.print("\n[dim]Sources:[/]")
        for source in response.sources_used[:3]:
            console.print(f"  [dim]{source}[/]")


@app.command()
def status() -> None:
    """Show the current status of the knowledge base."""
    from ....adapters.outbound.vector_store.qdrant_adapter import QdrantAdapter as QdrantVectorStore
    from ....config.settings import settings

    console.print("[bold]PitWallAI Status[/]\n")

    # Check API keys
    if settings.google_api_key:
        console.print("✅ Google API key configured")
    else:
        console.print("❌ Google API key not set (set GOOGLE_API_KEY in .env)")

    if settings.qdrant_url and settings.qdrant_api_key:
        console.print("✅ Qdrant credentials configured")
    else:
        console.print("❌ Qdrant credentials not set (set QDRANT_URL and QDRANT_API_KEY in .env)")
        return

    # Check knowledge base
    console.print("\n[bold]Knowledge Base (Qdrant Cloud):[/]")
    try:
        vector_store = QdrantVectorStore(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            embedding_api_key=settings.google_api_key,
        )

        total = 0
        for collection in ["regulations", "stewards_decisions", "race_data"]:
            stats = vector_store.get_collection_stats(collection)
            count = stats["count"]
            total += count
            emoji = "✅" if count > 0 else "⚪"
            console.print(f"  {emoji} {collection}: {count} documents")

        if total == 0:
            console.print(
                "\n[yellow]Knowledge base is empty. Run 'f1agent setup' to index data.[/]"
            )
        else:
            console.print(f"\n[green]Total: {total} indexed documents[/]")
    except Exception as exc:
        handle_cli_error(exc)


def _ingest_regulations(
    scraper: Any, vector_store: Any, limit: int, season: int, progress: Any
) -> int:
    """Ingest FIA regulations with progress tracking.

    Args:
        scraper: FIA scraper instance
        vector_store: Vector store instance
        limit: Number of items to process (0 = all)
        season: F1 season year
        progress: SetupProgress instance

    Returns:
        Number of documents indexed
    """
    from ....core.domain import Document
    from .progress import Phase

    config_hash = settings.get_config_hash()

    try:
        # DISCOVERY PHASE
        progress.start_phase(Phase.DISCOVERY, 0, f"Scanning regulations for {season}...")
        regulations = scraper.scrape_regulations(season)
        regs_to_process = regulations if limit == 0 else regulations[: limit * 2]
        progress.end_phase(f"Found {len(regs_to_process)} regulations")

        if not regs_to_process:
            return 0

        # DOWNLOAD PHASE
        progress.start_phase(Phase.DOWNLOAD, len(regs_to_process))
        reg_docs = []
        skipped = 0
        chunks_count = 0

        for i, reg in enumerate(regs_to_process):
            # Check if exists with current config
            if vector_store.document_exists("regulations", reg.url, config_hash):
                skipped += 1
                progress.mark_skipped(reg.title)
                continue

            try:
                progress.update(item_name=reg.title)
                scraper.download_document(reg)
                scraper.extract_text(reg)

                if reg.text_content:
                    # Normalize text to remove BOM and clean whitespace
                    clean_text = normalize_text(reg.text_content)
                    # Chunk long documents for better search
                    chunks = chunk_text(
                        clean_text,
                        chunk_size=settings.chunk_size,
                        chunk_overlap=settings.chunk_overlap,
                    )

                    # Use stable MD5 hash for ID
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
                    chunks_count += len(chunks)
                    progress.mark_new(reg.title)
            except Exception as e:
                progress.mark_failed(reg.title, str(e))

        progress.end_phase()
        progress.set_skipped_count(skipped)

        # EMBED & INDEX PHASE
        if reg_docs:
            progress.start_phase(Phase.INDEX, 1, f"Indexing {len(reg_docs)} chunks...")
            vector_store.add_documents(reg_docs, collection_name="regulations")
            progress.set_indexed_count(len(reg_docs), chunks_count)
            progress.end_phase(f"+{len(reg_docs)} documents")
            return len(reg_docs)

        return 0
    except Exception as exc:
        console.print(f"  [yellow]Warning: {exc}[/]")
        return 0


def _ingest_stewards_decisions(
    scraper: Any, vector_store: Any, limit: int, season: int, progress: Any
) -> int:
    """Ingest stewards decisions with progress tracking.

    Args:
        scraper: FIA scraper instance
        vector_store: Vector store instance
        limit: Number of items to process (0 = all)
        season: F1 season year
        progress: SetupProgress instance

    Returns:
        Number of documents indexed
    """
    from .progress import Phase
    from ....core.domain import Document

    config_hash = settings.get_config_hash()

    try:
        # DISCOVERY PHASE
        progress.start_phase(Phase.DISCOVERY, 0, f"Scanning stewards decisions for {season}...")
        decisions = scraper.scrape_stewards_decisions(season)
        decs_to_process = decisions if limit == 0 else decisions[: limit * 5]
        progress.end_phase(f"Found {len(decs_to_process)} decisions")

        if not decs_to_process:
            return 0

        # DOWNLOAD PHASE
        progress.start_phase(Phase.DOWNLOAD, len(decs_to_process))
        dec_docs = []
        skipped = 0
        chunks_count = 0

        for dec in decs_to_process:
            # Check if exists with current config
            if vector_store.document_exists("stewards_decisions", dec.url, config_hash):
                skipped += 1
                progress.mark_skipped(dec.title)
                continue

            try:
                progress.update(item_name=dec.title)
                scraper.download_document(dec)
                scraper.extract_text(dec)

                if dec.text_content:
                    # Normalize and chunk stewards decisions
                    clean_text = normalize_text(dec.text_content)
                    chunks = chunk_text(
                        clean_text,
                        chunk_size=settings.chunk_size,
                        chunk_overlap=settings.chunk_overlap,
                    )

                    # Stable MD5 hash
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
                    chunks_count += len(chunks)
                    progress.mark_new(dec.title)
            except Exception as e:
                progress.mark_failed(dec.title, str(e))

        progress.end_phase()
        progress.set_skipped_count(skipped)

        # INDEX PHASE
        if dec_docs:
            progress.start_phase(Phase.INDEX, 1, f"Indexing {len(dec_docs)} chunks...")
            vector_store.add_documents(dec_docs, collection_name="stewards_decisions")
            progress.set_indexed_count(len(dec_docs), chunks_count)
            progress.end_phase(f"+{len(dec_docs)} documents")
            return len(dec_docs)

        return 0
    except Exception as exc:
        console.print(f"  [yellow]Warning: {exc}[/]")
        return 0


def _ingest_race_data(
    cache_dir: Any, vector_store: Any, sql_adapter: Any, limit: int, season: int, progress: Any
) -> int:
    """Ingest race control data with progress tracking.

    Args:
        cache_dir: FastF1 cache directory
        vector_store: Vector store instance
        sql_adapter: SQL adapter instance
        limit: Number of races to process (0 = all)
        season: F1 season year
        progress: SetupProgress instance

    Returns:
        Number of documents indexed
    """
    from .progress import Phase
    from ....adapters.outbound.data_sources.fastf1_adapter import FastF1Adapter as FastF1Loader
    from ....core.domain import Document

    config_hash = settings.get_config_hash()

    try:
        # DISCOVERY PHASE
        progress.start_phase(Phase.DISCOVERY, 0, f"Scanning race events for {season}...")
        loader = FastF1Loader(cache_dir)
        events = loader.get_season_events(season)
        events_to_process = events if limit == 0 else events[:limit]
        progress.end_phase(f"Found {len(events_to_process)} races")

        if not events_to_process:
            return 0

        # Load Jolpica for driver context
        from ....adapters.outbound.data_sources.jolpica_adapter import (
            JolpicaAdapter as JolpicaClient,
        )

        jolpica = JolpicaClient()
        drivers = jolpica.get_drivers(season)
        driver_map = {d.code: d.name for d in drivers}
        driver_map.update({str(d.number): d.name for d in drivers if d.number})
        team_map = jolpica.get_driver_teams_map(season)

        # DOWNLOAD PHASE (loading race data)
        progress.start_phase(Phase.DOWNLOAD, len(events_to_process))
        race_docs = []
        skipped = 0
        new_count = 0

        for event in events_to_process:
            try:
                progress.update(item_name=event)
                penalties = loader.get_race_control_messages(season, event, "Race")
                event_new = 0

                for penalty in penalties:
                    if penalty.category in ["Penalty", "Investigation", "Track Limits"]:
                        # Resolve driver name using Jolpica data
                        driver_name = penalty.driver
                        if driver_name and driver_name in driver_map:
                            driver_name = driver_map[driver_name]

                        # Resolve team
                        team_name = penalty.team or "Unknown"
                        if team_name == "Unknown" and driver_name in team_map:
                            team_name = team_map[driver_name]

                        # Create synthetic URL for uniqueness check
                        msg_content = f"{event}-{penalty.session}-{penalty.message}"
                        msg_hash = hashlib.md5(msg_content.encode()).hexdigest()[:10]
                        synthetic_url = f"fastf1://{season}/{event}/{penalty.session}/{msg_hash}"

                        # Check if exists
                        if vector_store.document_exists("race_data", synthetic_url, config_hash):
                            skipped += 1
                            continue

                        content = normalize_text(
                            f"Race: {penalty.race_name} ({penalty.session})\n"
                            f"Driver: {driver_name or 'Unknown'}\n"
                            f"Team: {team_name}\n"
                            f"Message: {penalty.message}\n"
                            f"Category: {penalty.category}"
                        )

                        doc_id = f"race-{msg_hash}"

                        race_docs.append(
                            Document(
                                doc_id=doc_id,
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

                        event_new += 1

                        # Insert into SQL Database
                        if sql_adapter:
                            sql_adapter.insert_penalty(
                                season=season,
                                race_name=penalty.race_name,
                                driver=driver_name or "Unknown",
                                category=penalty.category,
                                message=penalty.message,
                                session=penalty.session,
                                team=team_name,
                            )

                if event_new > 0:
                    new_count += event_new

            except Exception as e:
                progress.mark_failed(event, str(e))
                continue

        progress.end_phase()
        progress.set_skipped_count(skipped)

        # INDEX PHASE
        if race_docs:
            progress.start_phase(Phase.INDEX, 1, f"Indexing {len(race_docs)} messages...")
            vector_store.add_documents(race_docs, collection_name="race_data")
            progress.set_indexed_count(len(race_docs))
            progress.end_phase(f"+{len(race_docs)} documents")
            return len(race_docs)

        return 0
    except Exception as exc:
        console.print(f"  [yellow]Warning: {exc}[/]")
        return 0


@app.command()
def setup(
    limit: int = typer.Option(0, help="Number of races to index (0 = all)"),
    reset: bool = typer.Option(False, help="Clear existing data before indexing"),
    season: int = typer.Option(2025, help="F1 season year to index"),
) -> None:
    """Index real F1 data into the knowledge base.

    This command scrapes FIA regulations and stewards decisions,
    and loads race control messages from FastF1.

    Use --limit 0 (default) to index ALL available data.
    Use --limit N to index only N races worth of data.
    """
    from pathlib import Path

    from ....adapters.outbound.data_sources.fia_adapter import FIAAdapter as FIAScraper
    from ....adapters.outbound.vector_store.qdrant_adapter import QdrantAdapter as QdrantVectorStore
    from ....config.settings import settings

    console.print("[bold]PitWallAI Setup[/]\n")

    # Check credentials
    if not settings.google_api_key:
        console.print("[red]Error: GOOGLE_API_KEY not set in .env[/]")
        raise typer.Exit(1)

    if not settings.qdrant_url or not settings.qdrant_api_key:
        console.print("[red]Error: QDRANT_URL and QDRANT_API_KEY not set in .env[/]")
        raise typer.Exit(1)

    console.print("[green]OK[/] Credentials configured")
    limit_str = "all" if limit == 0 else str(limit)
    console.print(f"[dim]Indexing data for {season} season (races: {limit_str})...[/]\n")

    try:
        vector_store = QdrantVectorStore(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            embedding_api_key=settings.google_api_key,
        )

        # Initialize SQL Adapter
        from ....adapters.outbound.sqlite_adapter import SQLiteAdapter

        sql_adapter = SQLiteAdapter()

        if reset:
            console.print("[yellow]Resetting collections and DB...[/]")
            vector_store.reset()
            sql_adapter.clear_season(season)  # Only clear specific season if reset? Or full clear?
            # 'reset' implies full reset, but 'season' implies partial setup.
            # Existing 'vector_store.reset()' clears ALL collections.
            # So we should probably clear FULL DB if reset is true?
            # But sql_adapter.clear_season(season) is safer if user just wants to re-index 2025.
            # Ideally 'f1agent setup' without --reset appends/updates?
            # Qdrant upserts by ID (safe).
            # SQLite inserts (duplicates!).
            # So we MUST clear the season from SQL before ingesting.
            pass

        # Always clear season data from SQL to avoid duplicates on re-run
        sql_adapter.clear_season(season)

        # Set up data directories
        data_dir = Path(settings.data_dir)
        cache_dir = data_dir / "fastf1_cache"
        data_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

        counts = {"regulations": 0, "stewards_decisions": 0, "race_data": 0}

        # Create progress tracker
        from .progress import SetupProgress

        progress = SetupProgress(console)

        # --- 1. Index FIA Regulations ---
        progress.start_data_type("Regulations", "📚")
        scraper = FIAScraper(data_dir)
        counts["regulations"] = _ingest_regulations(scraper, vector_store, limit, season, progress)

        # --- 2. Index Stewards Decisions ---
        progress.start_data_type("Stewards Decisions", "📋")
        counts["stewards_decisions"] = _ingest_stewards_decisions(
            scraper, vector_store, limit, season, progress
        )

        # --- 3. Index Race Data (penalties from FastF1) ---
        progress.start_data_type("Race Data", "🏎️")
        counts["race_data"] = _ingest_race_data(
            cache_dir, vector_store, sql_adapter, limit, season, progress
        )

        # Show final summary
        progress.finish()

        console.print(
            "\n[dim]Run 'pitwall ask \"What is the penalty for track limits?\"' to test[/]"
        )

    except Exception as exc:
        handle_cli_error(exc)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
