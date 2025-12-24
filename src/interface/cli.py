"""CLI interface for the F1 Penalty Agent."""

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

app = typer.Typer(
    name="f1agent",
    help="F1 Penalty Agent - Understand F1 penalties and regulations",
    add_completion=False,
)

# Fix Windows encoding issues with emojis
console = Console(force_terminal=True, legacy_windows=False)


def get_agent():
    """Get or create the F1 agent instance."""
    from ..agent.f1_agent import F1Agent
    from ..config import settings
    from ..llm.gemini_client import GeminiClient
    from ..rag.qdrant_store import QdrantVectorStore
    from ..rag.retriever import F1Retriever

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

    return F1Agent(llm, retriever)


@app.command()
def chat():
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
        agent = get_agent()
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
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question about F1 penalties or rules"),
):
    """Ask a single question and get an answer."""
    try:
        agent = get_agent()
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
def status():
    """Show the current status of the knowledge base."""
    from ..config import settings
    from ..rag.qdrant_store import QdrantVectorStore

    console.print("[bold]F1 Penalty Agent Status[/]\n")

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
    except Exception as e:
        console.print(f"[red]Error connecting to Qdrant: {e}[/]")


@app.command()
def setup(
    limit: int = typer.Option(3, help="Number of races to index (default: 3)"),
    reset: bool = typer.Option(False, help="Clear existing data before indexing"),
    season: int = typer.Option(2025, help="F1 season year to index"),
):
    """Index real F1 data into the knowledge base.

    This command scrapes FIA regulations and stewards decisions,
    and loads race control messages from FastF1.
    """
    from pathlib import Path

    from ..config import settings
    from ..data.fastf1_loader import FastF1Loader
    from ..data.fia_scraper import FIAScraper
    from ..rag.qdrant_store import Document, QdrantVectorStore

    console.print("[bold]F1 Penalty Agent Setup[/]\n")

    # Check credentials
    if not settings.google_api_key:
        console.print("[red]Error: GOOGLE_API_KEY not set in .env[/]")
        raise typer.Exit(1)

    if not settings.qdrant_url or not settings.qdrant_api_key:
        console.print("[red]Error: QDRANT_URL and QDRANT_API_KEY not set in .env[/]")
        raise typer.Exit(1)

    console.print("[green]OK[/] Credentials configured")
    console.print(f"[dim]Indexing data for {season} season (limit: {limit} races)...[/]\n")

    try:
        vector_store = QdrantVectorStore(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            embedding_api_key=settings.google_api_key,
        )

        if reset:
            console.print("[yellow]Resetting collections...[/]")
            vector_store.reset()

        # Set up data directories
        data_dir = Path(settings.data_dir)
        cache_dir = data_dir / "fastf1_cache"
        data_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

        counts = {"regulations": 0, "stewards_decisions": 0, "race_data": 0}

        # --- 1. Index FIA Regulations ---
        console.print("[bold]Scraping FIA regulations...[/]")
        try:
            scraper = FIAScraper(data_dir)
            regulations = scraper.scrape_regulations(season)

            reg_docs = []
            for reg in regulations[: limit * 2]:
                with console.status(f"[dim]Downloading {reg.title[:40]}...[/]"):
                    scraper.download_document(reg)
                    scraper.extract_text(reg)
                    if reg.text_content:
                        reg_docs.append(
                            Document(
                                doc_id=f"reg-{hash(reg.url) % 10000}",
                                content=reg.text_content[:10000],
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
            console.print(f"  [green]+{counts['regulations']}[/] regulations indexed")
        except Exception as e:
            console.print(f"  [yellow]Warning: {e}[/]")

        # --- 2. Index Stewards Decisions ---
        console.print("[bold]Scraping stewards decisions...[/]")
        try:
            decisions = scraper.scrape_stewards_decisions(season)

            dec_docs = []
            for dec in decisions[: limit * 5]:
                with console.status(f"[dim]Downloading {dec.title[:40]}...[/]"):
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
            console.print(f"  [green]+{counts['stewards_decisions']}[/] stewards decisions indexed")
        except Exception as e:
            console.print(f"  [yellow]Warning: {e}[/]")

        # --- 3. Index Race Data (penalties from FastF1) ---
        console.print("[bold]Loading race control data...[/]")
        try:
            loader = FastF1Loader(cache_dir)
            events = loader.get_season_events(season)

            race_docs = []
            for event in events[:limit]:
                with console.status(f"[dim]Loading {event}...[/]"):
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
                        console.print(f"  [dim]Skipped {event}: {e}[/]")
                        continue

            if race_docs:
                vector_store.add_documents(race_docs, collection_name="race_data")
                counts["race_data"] = len(race_docs)
            console.print(f"  [green]+{counts['race_data']}[/] race control messages indexed")
        except Exception as e:
            console.print(f"  [yellow]Warning: {e}[/]")

        total = sum(counts.values())
        console.print(f"\n[green bold]Setup complete! Indexed {total} documents.[/]")
        console.print("[dim]Run 'f1agent ask \"What is the penalty for track limits?\"' to test[/]")

    except Exception as e:
        console.print(f"[red]Error during setup: {e}[/]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
