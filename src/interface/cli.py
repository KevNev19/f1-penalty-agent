"""CLI interface for the F1 Penalty Agent."""

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

app = typer.Typer(
    name="f1agent",
    help="🏎️ F1 Penalty Agent - Understand F1 penalties and regulations",
    add_completion=False,
)
console = Console()


def get_agent(chroma_host: str | None = None, chroma_port: int | None = None):
    """Get or create the F1 agent instance.

    Args:
        chroma_host: Optional ChromaDB server host (overrides env var).
        chroma_port: Optional ChromaDB server port (overrides env var).
    """
    from ..agent.f1_agent import F1Agent
    from ..config import settings
    from ..llm.gemini_client import GeminiClient
    from ..rag.retriever import F1Retriever
    from ..rag.vectorstore import VectorStore

    settings.ensure_directories()

    if not settings.google_api_key:
        console.print(
            "[red]Error:[/] Google API key not set.\n"
            "Get a free key at https://aistudio.google.com/ and set GOOGLE_API_KEY in .env"
        )
        raise typer.Exit(1)

    # Use CLI args if provided, otherwise fall back to config/env vars
    host = chroma_host if chroma_host is not None else settings.chroma_host
    port = chroma_port if chroma_port is not None else settings.chroma_port

    # Use ChromaDB settings from config (supports K8s mode via CHROMA_HOST env var)
    vector_store = VectorStore(
        settings.chroma_persist_dir,
        settings.google_api_key,
        chroma_host=host,
        chroma_port=port,
    )
    retriever = F1Retriever(vector_store)
    llm = GeminiClient(settings.google_api_key, settings.llm_model)

    return F1Agent(llm, retriever)


@app.command()
def chat(
    chroma_host: str | None = typer.Option(
        None,
        "--chroma-host",
        help="ChromaDB server host (for K8s mode). Overrides CHROMA_HOST env var.",
    ),
    chroma_port: int | None = typer.Option(
        None,
        "--chroma-port",
        "-p",
        help="ChromaDB server port. Overrides CHROMA_PORT env var.",
    ),
):
    """Start an interactive chat session with the F1 agent."""
    console.print(
        Panel.fit(
            "[bold red]🏎️ F1 Penalty Agent[/]\n"
            "[dim]Ask questions about F1 penalties and regulations[/]\n\n"
            "Examples:\n"
            "• Why did Verstappen get a penalty in Austria?\n"
            "• What's the rule for track limits?\n"
            "• How are unsafe pit releases penalized?\n\n"
            "[dim]Type 'quit' or 'exit' to leave[/]",
            title="Welcome",
            border_style="red",
        )
    )

    try:
        agent = get_agent(chroma_host=chroma_host, chroma_port=chroma_port)
    except Exception as e:
        console.print(f"[red]Failed to initialize agent: {e}[/]")
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

            # Display the response
            console.print()
            console.print(
                Panel(
                    Markdown(response.answer),
                    title="[bold red]F1 Agent[/]",
                    border_style="red",
                )
            )

            # Show sources if available
            if response.sources_used:
                console.print("[dim]Sources used:[/]")
                for source in response.sources_used[:3]:
                    console.print(f"  [dim]{source}[/]")

        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye! 🏁[/]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question about F1 penalties or rules"),
    chroma_host: str | None = typer.Option(
        None,
        "--chroma-host",
        help="ChromaDB server host (for K8s mode). Overrides CHROMA_HOST env var.",
    ),
    chroma_port: int | None = typer.Option(
        None,
        "--chroma-port",
        "-p",
        help="ChromaDB server port. Overrides CHROMA_PORT env var.",
    ),
):
    """Ask a single question and get an answer."""
    try:
        agent = get_agent(chroma_host=chroma_host, chroma_port=chroma_port)
    except Exception as e:
        console.print(f"[red]Failed to initialize agent: {e}[/]")
        raise typer.Exit(1)

    with console.status("[bold green]Thinking...[/]"):
        response = agent.ask(question)

    console.print(Markdown(response.answer))

    if response.sources_used:
        console.print("\n[dim]Sources:[/]")
        for source in response.sources_used[:3]:
            console.print(f"  [dim]{source}[/]")


@app.command()
def setup(
    chroma_host: str | None = typer.Option(
        None,
        "--chroma-host",
        "-h",
        help="ChromaDB server host (for K8s mode). Default: use local PersistentClient.",
    ),
    chroma_port: int = typer.Option(8000, "--chroma-port", "-p", help="ChromaDB server port."),
    clean: bool = typer.Option(True, "--clean/--no-clean", "-c", help="Clean up orphaned files and reset database."),
    limit: int = typer.Option(0, "--limit", "-l", help="Limit number of documents to process (0 for all)."),
):
    """Download and index F1 regulations and data."""
    from rich.progress import track

    from ..config import settings
    from ..data.fastf1_loader import FastF1Loader
    from ..data.fia_scraper import FIAScraper
    from ..rag.retriever import F1Retriever
    from ..rag.vectorstore import VectorStore

    console.print("[bold]Setting up F1 Penalty Agent data...[/]\n")
    if chroma_host:
        console.print(f"[green]Using ChromaDB server at {chroma_host}:{chroma_port}[/]\n")

    settings.ensure_directories()

    # Initialize components with optional K8s ChromaDB
    vector_store = VectorStore(
        settings.chroma_persist_dir,
        settings.google_api_key,
        chroma_host=chroma_host,
        chroma_port=chroma_port,
    )
    retriever = F1Retriever(vector_store)

    # Load FastF1 data first to get race context
    console.print("\n[bold blue]Step 0: Initializing Race Context...[/]")
    target_race_names = []
    try:
        loader = FastF1Loader(settings.cache_dir)
        races = loader.get_season_events(2025)

        if races:
            console.print(f"  Found {len(races)} races for 2025")
            # For demo/limit purposes, pick specific races
            # Default to "Abu Dhabi Grand Prix" (End of season, likely on recent page)
            if "Abu Dhabi Grand Prix" in races:
                target_race_names = ["Abu Dhabi Grand Prix"]
                console.print("  [green]Focusing on: Abu Dhabi Grand Prix[/]")
            elif "Australian Grand Prix" in races:
                target_race_names = ["Australian Grand Prix"]
                console.print("  [green]Focusing on: Australian Grand Prix[/]")
            else:
                target_race_names = races[:3]
                console.print(f"  [green]Focusing on first {len(target_race_names)} races[/]")
        else:
            console.print("  [dim]No races found in schedule[/]")
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load race schedule: {e}[/]")

    # Scrape FIA documents with context
    console.print("\n[bold blue]Step 1: Checking for documents...[/]")
    scraper = FIAScraper(settings.data_dir)

    try:
        # If limit is used, use "Smart Mode": All Regulations + Decisions for Target Race
        if limit > 0 and target_race_names:
             console.print(f"[dim]Smart Mode: Fetching Regulations + Decisions for {target_race_names[0]}[/]")
             documents = []
             # 1. Get All Sporting Regulations (Critical)
             # Optimization: Only re-scrape regs if cleaning or not in incremental mode
             # But for now, let's always get them to be safe, UNLESS we are explicitly doing an incremental fix
             # For the "Fix Missing Decisions" fast path, we skip regs if clean=False
             if clean:
                 regs = scraper.scrape_regulations(season=2025)
                 documents.extend(regs)
             else:
                 console.print("  [dim]Skipping regulations (Incremental update)...[/]")
             
             # 2. Get Decisions for Target Race
             for race in target_race_names:
                 decs = scraper.scrape_stewards_decisions(season=2025, race_name=race)
                 documents.extend(decs)
                 
             console.print(f"  Found {len(documents)} context-aware documents")
        else:
             # Standard behavior
             documents = scraper.get_available_documents(season=2025, limit=limit)
             console.print(f"  Found {len(documents)} documents available")

        # Cleanup orphaned files
        if clean:
            scraper.cleanup_orphaned_files(documents)

        # Download missing files
        console.print("\n[bold blue]Step 2: verifying downloads...[/]")
        downloaded = 0
        skipped = 0
        for doc in track(documents, description="Verifying/Downloading..."):
            if scraper.download_document(doc):
                downloaded += 1
            else:
                skipped += 1
        console.print(f"  [green]Downloaded {downloaded} new files, verified {skipped} existing[/]")

        # Extract text
        console.print("\n[bold blue]Step 3: Processing text content...[/]")
        processed = 0
        for doc in track(documents, description="Extracting text..."):
            scraper.extract_text(doc)
            if doc.text_content:
                processed += 1
        console.print(f"  [green]Successfully processed text from {processed} documents[/]")

        # Reset DB
        if clean:
            console.print("\n[bold blue]Step 3.5: Resetting database...[/]")
            vector_store.reset()

        # Index documents
        console.print("\n[bold blue]Step 4: Indexing documents...[/]")
        indexed_count = 0
        for i, doc in enumerate(documents):
            fname = doc.local_path.name if doc.local_path else doc.title
            console.print(f"[dim]Indexing {i+1}/{len(documents)}: {fname}[/]")
            if doc.text_content:
                chunks = retriever.index_fia_document(doc)
                if chunks > 0:
                    indexed_count += 1
        console.print(f"  [green]Indexed {indexed_count} documents[/]")

    except Exception as e:
        console.print(f"[yellow]Warning: Could not process documents: {e}[/]")
        console.print("[dim]This may be due to website changes. You can add documents manually.[/]")
        import traceback
        traceback.print_exc()

    # Load FastF1 data for the SAME target races
    console.print("\n[bold blue]Step 5: Loading race data...[/]")
    try:
        # Use existing loader
        if target_race_names:
             for race in target_race_names:
                try:
                    penalties = loader.get_race_control_messages(2025, race, "Race")
                    for penalty in penalties:
                        retriever.index_penalty_event(penalty)
                except Exception as e:
                    console.print(f"[dim]  Could not load {race}: {e}[/]")
        elif races:
             # Fallback if filtered list empty but races exist
             for race in races[:3]:
                 try:
                    penalties = loader.get_race_control_messages(2025, race, "Race")
                    for penalty in penalties:
                        retriever.index_penalty_event(penalty)
                 except Exception:
                     pass
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load race data: {e}[/]")

    # Show stats
    console.print("\n[bold green]Setup complete![/]")
    console.print("\n[bold]Knowledge base statistics:[/]")

    for collection in ["f1_regulations", "stewards_decisions", "race_data"]:
        stats = vector_store.get_collection_stats(collection)
        console.print(f"  {collection}: {stats['count']} documents")

    console.print("\n[dim]Run 'poetry run f1agent chat' to start chatting![/]")


@app.command()
def status():
    """Show the current status of the knowledge base."""
    from ..config import settings
    from ..rag.vectorstore import VectorStore

    settings.ensure_directories()

    vector_store = VectorStore(
        settings.chroma_persist_dir,
        settings.google_api_key,
        chroma_host=settings.chroma_host,
        chroma_port=settings.chroma_port,
    )

    console.print("[bold]F1 Penalty Agent Status[/]\n")

    # Check API key
    if settings.google_api_key:
        console.print("✅ Google API key configured")
    else:
        console.print("❌ Google API key not set (set GOOGLE_API_KEY in .env)")

    # Check knowledge base
    console.print("\n[bold]Knowledge Base:[/]")
    total = 0
    for collection in ["f1_regulations", "stewards_decisions", "race_data"]:
        stats = vector_store.get_collection_stats(collection)
        count = stats["count"]
        total += count
        emoji = "✅" if count > 0 else "⚪"
        console.print(f"  {emoji} {collection}: {count} documents")

    if total == 0:
        console.print("\n[yellow]Knowledge base is empty. Run 'f1agent setup' first.[/]")
    else:
        console.print(f"\n[green]Total: {total} indexed documents[/]")


if __name__ == "__main__":
    app()
