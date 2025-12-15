"""Document retriever with text chunking and context building."""

import hashlib
import re
from dataclasses import dataclass

from rich.console import Console

from ..data.fastf1_loader import PenaltyEvent
from ..data.fia_scraper import FIADocument
from .vectorstore import Document, SearchResult, VectorStore

console = Console()


@dataclass
class RetrievalContext:
    """Context retrieved for answering a question."""

    regulations: list[SearchResult]
    stewards_decisions: list[SearchResult]
    race_data: list[SearchResult]
    query: str

    def get_combined_context(self, max_chars: int = 8000) -> str:
        """Get combined context string for the LLM.

        Args:
            max_chars: Maximum characters to include.

        Returns:
            Formatted context string, or informative message if no context found.
        """
        parts = []
        char_count = 0

        # Add regulations first (most authoritative)
        if self.regulations:
            parts.append("=== FIA REGULATIONS ===")
            for result in self.regulations:
                if char_count > max_chars:
                    break
                content = result.document.content
                source = result.document.metadata.get("source", "Unknown")
                parts.append(f"\n[Source: {source}]\n{content}")
                char_count += len(content)

        # Add stewards decisions (specific examples)
        if self.stewards_decisions:
            parts.append("\n\n=== STEWARDS DECISIONS ===")
            for result in self.stewards_decisions:
                if char_count > max_chars:
                    break
                content = result.document.content
                event = result.document.metadata.get("event", "Unknown")
                parts.append(f"\n[Event: {event}]\n{content}")
                char_count += len(content)

        # Add race data (live events)
        if self.race_data:
            parts.append("\n\n=== RACE CONTROL MESSAGES ===")
            for result in self.race_data:
                if char_count > max_chars:
                    break
                content = result.document.content
                parts.append(f"\n{content}")
                char_count += len(content)

        # Return informative message if no context found
        if not parts:
            return "No specific regulatory context found for this query. Please provide a general response based on F1 knowledge."

        return "\n".join(parts)


class F1Retriever:
    """Retrieves relevant F1 documents for answering questions."""

    def __init__(self, vector_store: VectorStore) -> None:
        """Initialize the retriever.

        Args:
            vector_store: VectorStore instance for document retrieval.
        """
        self.vector_store = vector_store

    def chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> list[str]:
        """Split text into overlapping chunks.

        Args:
            text: Text to chunk.
            chunk_size: Target size of each chunk (must be positive).
            chunk_overlap: Overlap between consecutive chunks (must be less than chunk_size).

        Returns:
            List of text chunks.

        Raises:
            ValueError: If chunk_overlap >= chunk_size or parameters are invalid.
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size to avoid infinite loop")

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence-ending punctuation
                for punct in [". ", ".\n", "? ", "?\n", "! ", "!\n"]:
                    last_punct = text.rfind(punct, start, end)
                    if last_punct > start + chunk_size // 2:
                        end = last_punct + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - chunk_overlap

        return chunks

    def index_fia_document(
        self,
        document: FIADocument,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> int:
        """Index an FIA document into the vector store.

        Args:
            document: FIA document to index.
            chunk_size: Size of text chunks.
            chunk_overlap: Overlap between chunks.

        Returns:
            Number of chunks indexed.
        """
        if not document.text_content:
            console.print(f"[yellow]No text content in {document.title}[/]")
            return 0

        # Chunk the document
        chunks = self.chunk_text(document.text_content, chunk_size, chunk_overlap)

        # Create Document objects with metadata
        # Use hash of full title + URL to avoid ID collisions
        title_hash = hashlib.md5(f"{document.title}_{document.url}".encode()).hexdigest()[:8]
        docs = []
        for i, chunk in enumerate(chunks):
            doc = Document(
                content=chunk,
                metadata={
                    "source": document.title,
                    "doc_type": document.doc_type,
                    "event": document.event_name or "",
                    "season": document.season,
                    "chunk_index": i,
                    "url": document.url,
                },
                doc_id=f"{document.doc_type}_{title_hash}_{i}",
            )
            docs.append(doc)

        # Add to appropriate collection
        if document.doc_type == "regulation":
            collection = VectorStore.REGULATIONS_COLLECTION
        else:
            collection = VectorStore.STEWARDS_COLLECTION

        return self.vector_store.add_documents(docs, collection)

    def index_penalty_event(self, event: PenaltyEvent) -> int:
        """Index a penalty event from race control.

        Args:
            event: Penalty event to index.

        Returns:
            Number of documents indexed (1 or 0).
        """
        # Create a readable description
        content = f"""
Race: {event.race_name} {event.season}
Session: {event.session}
Category: {event.category}
Driver: {event.driver or "Unknown"}
Time: {event.time or "Unknown"}

Message: {event.message}

{event.details or ""}
        """.strip()

        # Use hash to create unique doc_id and avoid collisions
        msg_hash = hashlib.md5(
            f"{event.race_name}_{event.season}_{event.message}".encode()
        ).hexdigest()[:8]
        doc = Document(
            content=content,
            metadata={
                "race": event.race_name,
                "season": event.season,
                "session": event.session,
                "category": event.category,
                "driver": event.driver or "",
            },
            doc_id=f"penalty_{event.race_name}_{event.season}_{msg_hash}".replace(" ", "_"),
        )

        return self.vector_store.add_documents([doc], VectorStore.RACE_DATA_COLLECTION)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        include_regulations: bool = True,
        include_stewards: bool = True,
        include_race_data: bool = True,
    ) -> RetrievalContext:
        """Retrieve relevant context for a query.

        Args:
            query: User's question.
            top_k: Number of results per category.
            include_regulations: Whether to search regulations.
            include_stewards: Whether to search stewards decisions.
            include_race_data: Whether to search race control data.

        Returns:
            RetrievalContext with relevant documents.
        """
        regulations = []
        stewards = []
        race_data = []

        if include_regulations:
            regulations = self.vector_store.search(query, VectorStore.REGULATIONS_COLLECTION, top_k)

        if include_stewards:
            stewards = self.vector_store.search(query, VectorStore.STEWARDS_COLLECTION, top_k)

        if include_race_data:
            race_data = self.vector_store.search(query, VectorStore.RACE_DATA_COLLECTION, top_k)

        return RetrievalContext(
            regulations=regulations,
            stewards_decisions=stewards,
            race_data=race_data,
            query=query,
        )

    def extract_race_context(self, query: str) -> dict:
        """Extract race/driver context from a query.

        Args:
            query: User's question.

        Returns:
            Dict with extracted context (race, driver, season, etc.)
        """
        context = {
            "driver": None,
            "race": None,
            "season": None,
        }

        # Common driver names/codes
        driver_patterns = [
            (r"\bVerstappen\b", "Max Verstappen"),
            (r"\bHamilton\b", "Lewis Hamilton"),
            (r"\bNorris\b", "Lando Norris"),
            (r"\bLeclerc\b", "Charles Leclerc"),
            (r"\bSainz\b", "Carlos Sainz"),
            (r"\bRussell\b", "George Russell"),
            (r"\bPerez\b", "Sergio Perez"),
            (r"\bAlonso\b", "Fernando Alonso"),
            (r"\bPiastri\b", "Oscar Piastri"),
            (r"\bStroll\b", "Lance Stroll"),
            (r"\bVER\b", "Max Verstappen"),
            (r"\bHAM\b", "Lewis Hamilton"),
            (r"\bNOR\b", "Lando Norris"),
        ]

        for pattern, driver_name in driver_patterns:
            if re.search(pattern, query, re.I):
                context["driver"] = driver_name
                break

        # Race names
        race_patterns = [
            "Bahrain",
            "Saudi Arabian",
            "Australian",
            "Japanese",
            "Chinese",
            "Miami",
            "Monaco",
            "Spanish",
            "Canadian",
            "Austrian",
            "British",
            "Hungarian",
            "Belgian",
            "Dutch",
            "Italian",
            "Azerbaijan",
            "Singapore",
            "United States",
            "Mexican",
            "Brazilian",
            "Las Vegas",
            "Qatar",
            "Abu Dhabi",
            "Silverstone",
            "Monza",
            "Spa",
            "Imola",
        ]

        for race in race_patterns:
            if re.search(rf"\b{race}\b", query, re.I):
                context["race"] = race
                break

        # Season/year - support years from 2000 onwards
        year_match = re.search(r"\b(20[0-9]{2})\b", query)
        if year_match:
            year = int(year_match.group(1))
            # Validate reasonable F1 season range (F1 started in 1950, but modern era starts ~2000)
            if 2000 <= year <= 2099:
                context["season"] = year

        return context
