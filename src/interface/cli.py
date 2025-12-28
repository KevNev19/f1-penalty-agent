from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from ..application.services.ask_question import AskQuestionService
from ..common.utils import chunk_text
from ..composition.container import get_ask_service

app = typer.Typer(
    name="f1agent",
    help="F1 Penalty Agent - Understand F1 penalties and regulations",
    add_completion=False,
)

# Fix Windows encoding issues with emojis
console = Console(force_terminal=True, legacy_windows=False)


def get_service() -> AskQuestionService:
    """Get or create the AskQuestionService instance."""
    from ..config import settings

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

    return get_ask_service()


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
        service = get_service()
    except Exception as e:  # noqa: BLE001
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
                response = service.ask(query)

            console.print()
            console.print(
                Panel(
                    Markdown(response.text),
                    title="[bold red]F1 Agent[/]",
                    border_style="red",
                )
            )

            if response.sources:
                console.print("[dim]Sources used:[/]")
                for source in response.sources[:3]:
                    console.print(f"  [dim]{source.title}[/]")

        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye! 🏁[/]")
            break
        except Exception as e:  # noqa: BLE001
            console.print(f"[red]Error: {e}[/]")


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question about F1 penalties or rules"),
):
    """Ask a single question and get an answer."""
    try:
        service = get_service()
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Failed to initialize agent: {e}[/]")
        raise typer.Exit(1)

    with console.status("[bold green]Thinking...[/]"):
        response = service.ask(question)

    console.print(Markdown(response.text))

    if response.sources:
        console.print("\n[dim]Sources:[/]")
        for source in response.sources[:3]:
            console.print(f"  [dim]{source.title}[/]")


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
    except Exception as e:  # noqa: BLE001
        console.print(f"[red]Error connecting to Qdrant: {e}[/]")


@app.command()
def setup(
    limit: int = typer.Option(0, help="Number of races to index (0 = all)"),
    reset: bool = typer.Option(False, help="Clear existing data before indexing"),
    season: int = typer.Option(2025, help="F1 season year to index"),
):
    """Index real F1 data into the knowledge base.

    This command scrapes FIA regulations and stewards decisions,
    and loads race control messages from FastF1.

    Use --limit 0 (default) to index ALL available data.
    Use --limit N to index only N races worth of data.
    """
    from ..config import settings
    from ..data.fastf1_loader import FastF1Loader
    from ..data.fia_scraper import FIADocument, FIAScraper
    from ..rag.qdrant_store import QdrantVectorStore
    from ..rag.retriever import F1Retriever

    settings.ensure_directories()

    if not settings.google_api_key:
        console.print("[red]Error:[/] GOOGLE_API_KEY not set in environment.")
        raise typer.Exit(1)

    # Initialize vector store and retriever
    vector_store = QdrantVectorStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        embedding_api_key=settings.google_api_key,
    )
    retriever = F1Retriever(vector_store, use_reranker=True)

    if reset:
        console.print("[yellow]Resetting collections...[/]")
        vector_store.reset_collections()

    console.print("[green]Downloading FIA documents and stewards decisions...[/]")
    scraper = FIAScraper(data_dir=Path(settings.data_dir))
    fia_docs: list[FIADocument] = scraper.fetch_documents(limit=limit, season=season)

    total_indexed = 0
    for doc in fia_docs:
        indexed = retriever.index_fia_document(doc)
        total_indexed += indexed
        console.print(f"Indexed {indexed} chunks from {doc.title}")

    console.print("[green]Loading race control messages...[/]")
    f1_loader = FastF1Loader(data_dir=Path(settings.data_dir))
    penalty_events = f1_loader.load_penalty_events(limit=limit, season=season)

    for event in penalty_events:
        retriever.index_penalty_event(event)

    console.print(
        Panel.fit(
            f"[bold green]Setup complete![/]\nIndexed {total_indexed} regulation/stewards chunks\n"
            f"Loaded {len(penalty_events)} race control events",
            title="Success",
            border_style="green",
        )
    )


@app.command()
def chunk(
    path: Path = typer.Argument(..., help="Path to a text file to chunk"),
    chunk_size: int = typer.Option(1000, help="Size of each chunk"),
    chunk_overlap: int = typer.Option(200, help="Overlap between chunks"),
):
    """Chunk a text file and display the chunks."""
    content = path.read_text(encoding="utf-8")
    chunks = chunk_text(content, chunk_size, chunk_overlap)

    console.print(f"[bold]Generated {len(chunks)} chunks:[/]")
    for i, chunk in enumerate(chunks, 1):
        console.print(Panel.fit(chunk, title=f"Chunk {i}"))
