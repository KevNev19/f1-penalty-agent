"""Domain models for F1 Penalty Agent.

This package contains all data models used across the application.
Models are organized by domain area:

- document: Document and SearchResult for the RAG vector store
- fia_document: FIADocument for scraped FIA documents
- race_data: PenaltyEvent and RaceResult from FastF1
- agent: QueryType, AgentResponse, and RetrievalContext

All models are re-exported here for convenient importing:

    from src.core.domain import Document, SearchResult, FIADocument
"""

from .agent import AgentResponse, QueryType, RetrievalContext
from .document import Document, SearchResult
from .fia_document import FIADocument
from .race_data import PenaltyEvent, RaceResult

__all__ = [
    # Document models
    "Document",
    "SearchResult",
    # FIA document models
    "FIADocument",
    # Race data models
    "PenaltyEvent",
    "RaceResult",
    # Agent models
    "QueryType",
    "AgentResponse",
    "RetrievalContext",
]
