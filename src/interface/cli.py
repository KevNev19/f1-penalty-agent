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


def get_agent():
    """Get or create the F1 agent instance."""
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

    # Use ChromaDB settings from config (supports K8s mode via CHROMA_HOST env var)
    vector_store = VectorStore(
        settings.chroma_persist_dir,
        settings.google_api_key,
        chroma_host=settings.chroma_host,
        chroma_port=settings.chroma_port,
    )
    retriever = F1Retriever(vector_store)
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

            # Display the response
            console.print()
            console.print(Panel(
                Markdown(response.answer),
                title="[bold red]F1 Agent[/]",
                border_style="red",
            ))

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
def setup(
    chroma_host: str | None = typer.Option(
        None, "--chroma-host", "-h",
        help="ChromaDB server host (for K8s mode). Default: use local PersistentClient."
    ),
    chroma_port: int = typer.Option(
        8000, "--chroma-port", "-p",
        help="ChromaDB server port."
    ),
):
    """Download and index F1 regulations and data."""
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

    # Scrape FIA documents
    console.print("[bold blue]Step 1: Scraping FIA documents...[/]")
    scraper = FIAScraper(settings.data_dir)

    try:
        documents = scraper.get_all_documents(season=2025)
        console.print(f"  Found {len(documents)} documents")

        # Index documents
        console.print("\n[bold blue]Step 2: Indexing documents...[/]")
        for doc in documents:
            if doc.text_content:
                chunks = retriever.index_fia_document(doc)
                console.print(f"  Indexed {chunks} chunks from {doc.title[:50]}")
    except Exception as e:
        console.print(f"[yellow]Warning: Could not scrape FIA documents: {e}[/]")
        console.print("[dim]This may be due to website changes. You can add documents manually.[/]")

    # Load FastF1 data
    console.print("\n[bold blue]Step 3: Loading race data...[/]")
    try:
        loader = FastF1Loader(settings.cache_dir)
        races = loader.get_season_events(2025)

        if races:
            console.print(f"  Found {len(races)} races for 2025")
            # Load a sample race for testing
            for race in races[:3]:  # First 3 races
                try:
                    penalties = loader.get_race_control_messages(2025, race, "Race")
                    for penalty in penalties:
                        retriever.index_penalty_event(penalty)
                except Exception as e:
                    console.print(f"[dim]  Could not load {race}: {e}[/]")
        else:
            console.print("  [dim]No races found (season may not have started)[/]")
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

    vector_store = VectorStore(settings.chroma_persist_dir, settings.google_api_key)

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
