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
            console.print("\n[yellow]Knowledge base is empty. Index data first.[/]")
        else:
            console.print(f"\n[green]Total: {total} indexed documents[/]")
    except Exception as e:
        console.print(f"[red]Error connecting to Qdrant: {e}[/]")


@app.command()
def setup(
    limit: int = typer.Option(3, help="Number of races to index (default: 3)"),
    reset: bool = typer.Option(False, help="Clear existing data before indexing"),
):
    """Index F1 data into the knowledge base."""
    from ..config import settings
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
    console.print(f"[dim]Indexing {limit} races worth of data...[/]\n")

    try:
        vector_store = QdrantVectorStore(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            embedding_api_key=settings.google_api_key,
        )

        if reset:
            console.print("[yellow]Resetting collections...[/]")
            vector_store.reset()

        # Index regulations (mock for now - would load from FIA docs)
        console.print("[bold]Indexing regulations...[/]")
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
        console.print(f"  [green]+{len(regulations)}[/] regulations indexed")

        # Index some sample stewards decisions
        console.print("[bold]Indexing stewards decisions...[/]")
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
        console.print(f"  [green]+{len(decisions)}[/] stewards decisions indexed")

        console.print("\n[green bold]Setup complete![/]")
        console.print("[dim]Run 'f1agent ask \"What is the penalty for track limits?\"' to test[/]")

    except Exception as e:
        console.print(f"[red]Error during setup: {e}[/]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
