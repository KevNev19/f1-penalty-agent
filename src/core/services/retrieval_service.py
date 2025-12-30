"""Document retriever with text chunking and context building."""

import hashlib
import logging
import re

from ..domain import Document, FIADocument, PenaltyEvent, RetrievalContext, SearchResult
from ..domain.utils import chunk_text
from ..ports.vector_store_port import VectorStorePort
from .reranker import CrossEncoderReranker

logger = logging.getLogger(__name__)


class RetrievalService:
    """Retrieves relevant F1 documents for answering questions."""

    # F1-specific synonyms for query expansion
    F1_SYNONYMS = {
        "penalty": ["sanction", "punishment", "time penalty", "grid penalty", "reprimand"],
        "5 second": ["five second", "5s", "five-second"],
        "10 second": ["ten second", "10s", "ten-second"],
        "track limits": [
            "track boundaries",
            "running wide",
            "exceeding track limits",
            "leaving the track",
        ],
        "impeding": ["blocking", "held up", "obstructing", "getting in the way"],
        "unsafe release": ["dangerous release", "pit release", "pit lane incident"],
        "collision": ["crash", "contact", "incident", "accident", "hit"],
        "overtaking": ["passing", "overtake", "pass"],
        "qualifying": ["quali", "Q1", "Q2", "Q3"],
        "DRS": ["drag reduction system", "rear wing"],
        "parc ferme": ["parc fermé", "post-race", "impound"],
        "grid": ["starting grid", "starting position", "grid position"],
        "stewards": ["race stewards", "FIA stewards", "officials"],
        "reprimand": ["warning", "formal warning"],
        "disqualification": ["DSQ", "disqualified", "excluded"],
        "black flag": ["disqualification flag", "black flag meatball"],
        "safety car": ["SC", "virtual safety car", "VSC"],
        "red flag": ["race stopped", "session stopped"],
    }

    def __init__(
        self,
        vector_store: VectorStorePort,
        use_reranker: bool = True,
    ) -> None:
        """Initialize the retriever.

        Args:
            vector_store: QdrantVectorStore instance for document retrieval.
            use_reranker: Whether to use cross-encoder re-ranking for better precision.
        """
        self.vector_store = vector_store
        self.reranker = CrossEncoderReranker() if use_reranker else None
        if self.reranker:
            logger.info("Cross-encoder re-ranking enabled")

    def expand_query(self, query: str) -> str:
        """Expand query with F1-specific synonyms for better retrieval.

        Args:
            query: Original user query.

        Returns:
            Expanded query with relevant synonyms added.
        """
        query_lower = query.lower()
        expansions = []

        for term, synonyms in self.F1_SYNONYMS.items():
            if term in query_lower:
                # Add relevant synonyms (limit to 2 to avoid query dilution)
                expansions.extend(synonyms[:2])

        if expansions:
            # Append expansions to original query
            return f"{query} {' '.join(expansions)}"
        return query

    def boost_keyword_matches(self, results: list[SearchResult], query: str) -> list[SearchResult]:
        """Boost scores for results that contain exact keyword matches.

        Args:
            results: List of search results.
            query: Original query to check for keyword matches.

        Returns:
            Results with adjusted scores for keyword matches.
        """
        keywords = [w.lower() for w in query.split() if len(w) > 3]

        for result in results:
            content_lower = result.document.content.lower()
            match_count = sum(1 for kw in keywords if kw in content_lower)

            # Boost score by up to 10% based on keyword matches
            if match_count > 0:
                boost = min(0.1, match_count * 0.02)  # 2% per keyword, max 10%
                result.score = min(1.0, result.score + boost)

        # Re-sort by boosted scores
        results.sort(key=lambda x: x.score, reverse=True)
        return results

    def deduplicate_results(self, results: list[SearchResult]) -> list[SearchResult]:
        """Remove duplicate results based on source and content similarity.

        Args:
            results: List of search results (already sorted by score).

        Returns:
            Deduplicated list of results.
        """
        seen_sources = set()
        deduplicated = []

        for result in results:
            # Create a source key for deduplication
            source = result.document.metadata.get("source", "")
            # Use first 200 chars of content as part of the key
            content_key = result.document.content[:200] if result.document.content else ""
            dedup_key = f"{source}:{hash(content_key)}"

            if dedup_key not in seen_sources:
                seen_sources.add(dedup_key)
                deduplicated.append(result)

        return deduplicated

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
            logger.warning(f"No text content in {document.title}")
            return 0

        # Chunk the document
        chunks = chunk_text(document.text_content, chunk_size, chunk_overlap)

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
            collection = VectorStorePort.REGULATIONS_COLLECTION
        else:
            collection = VectorStorePort.STEWARDS_COLLECTION

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

        return self.vector_store.add_documents([doc], VectorStorePort.RACE_DATA_COLLECTION)

    def _retrieve_regulations(
        self, query: str, expanded_query: str, top_k: int, retrieve_k: int
    ) -> list[SearchResult]:
        """Retrieve and process regulations."""
        # Regulations don't use context filters (search all)
        regulations = self.vector_store.search(
            expanded_query, VectorStorePort.REGULATIONS_COLLECTION, retrieve_k
        )
        # Apply keyword boosting and deduplication
        regulations = self.boost_keyword_matches(regulations, query)
        regulations = self.deduplicate_results(regulations)

        # Apply reranking if available
        if self.reranker and regulations:
            regulations = self.reranker.rerank(query, regulations, top_k)
        else:
            regulations = regulations[:top_k]

        return regulations

    def _retrieve_stewards(
        self,
        query: str,
        expanded_query: str,
        top_k: int,
        retrieve_k: int,
        filter_metadata: dict | None,
    ) -> list[SearchResult]:
        """Retrieve and process stewards decisions."""
        # Try with filter first, fallback to no filter if no results
        stewards = self.vector_store.search(
            expanded_query, VectorStorePort.STEWARDS_COLLECTION, top_k, filter_metadata
        )
        # If no results with filter, try without filter
        if not stewards and filter_metadata:
            stewards = self.vector_store.search(
                expanded_query, VectorStorePort.STEWARDS_COLLECTION, retrieve_k
            )
        # Apply keyword boosting and deduplication
        stewards = self.boost_keyword_matches(stewards, query)
        stewards = self.deduplicate_results(stewards)

        # Apply reranking if available
        if self.reranker and stewards:
            stewards = self.reranker.rerank(query, stewards, top_k)
        else:
            stewards = stewards[:top_k]

        return stewards

    def _retrieve_race_data(
        self,
        query: str,
        expanded_query: str,
        top_k: int,
        retrieve_k: int,
        filter_metadata: dict | None,
    ) -> list[SearchResult]:
        """Retrieve and process race data."""
        # Try with filter first, fallback to no filter if no results
        race_data = self.vector_store.search(
            expanded_query, VectorStorePort.RACE_DATA_COLLECTION, top_k, filter_metadata
        )
        # If no results with filter, try without filter
        if not race_data and filter_metadata:
            race_data = self.vector_store.search(
                expanded_query, VectorStorePort.RACE_DATA_COLLECTION, retrieve_k
            )
        # Apply keyword boosting and deduplication
        race_data = self.boost_keyword_matches(race_data, query)
        race_data = self.deduplicate_results(race_data)

        # Apply reranking if available
        if self.reranker and race_data:
            race_data = self.reranker.rerank(query, race_data, top_k)
        else:
            race_data = race_data[:top_k]

        return race_data

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        include_regulations: bool = True,
        include_stewards: bool = True,
        include_race_data: bool = True,
        query_context: dict | None = None,
    ) -> RetrievalContext:
        """Retrieve relevant context for a query.

        Args:
            query: User's question.
            top_k: Number of results per category.
            include_regulations: Whether to search regulations.
            include_stewards: Whether to search stewards decisions.
            include_race_data: Whether to search race control data.
            query_context: Optional dict with detected driver/race/season context
                          for filtering stewards_decisions and race_data.

        Returns:
            RetrievalContext with relevant documents.
        """
        regulations = []
        stewards = []
        race_data = []

        # Expand query with F1 synonyms for better retrieval
        expanded_query = self.expand_query(query)

        # Build metadata filters from query context
        # Note: ChromaDB supports $eq, $ne, $gt, $gte, $lt, $lte, $in, $nin
        # For text matching in content, we rely on the embedding search instead
        # stewards_filter = None # Stewards decisions don't have reliable metadata fields for filtering yet
        race_filter = None

        if query_context:
            # For race_data, filter by season if available (integer comparison)
            if query_context.get("season"):
                race_filter = {"season": {"$eq": query_context["season"]}}

        # Determine how many candidates to retrieve
        # If using reranker, get more candidates for re-ranking
        retrieve_k = top_k * 4 if self.reranker else top_k

        if include_regulations:
            regulations = self._retrieve_regulations(query, expanded_query, top_k, retrieve_k)

        if include_stewards:
            # Stewards don't use reliable metadata filters yet
            stewards = self._retrieve_stewards(query, expanded_query, top_k, retrieve_k, None)

        if include_race_data:
            race_data = self._retrieve_race_data(
                query, expanded_query, top_k, retrieve_k, race_filter
            )

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
