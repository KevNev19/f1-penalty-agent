"""FastAPI dependency injection for F1 Agent."""

import logging
from functools import lru_cache

from ....adapters.outbound.llm.gemini_adapter import GeminiAdapter as GeminiClient
from ....adapters.outbound.vector_store.qdrant_adapter import QdrantAdapter as QdrantVectorStore
from ....config.settings import settings
from ....core.services.agent_service import AgentService as F1Agent
from ....core.services.retrieval_service import RetrievalService as F1Retriever

logger = logging.getLogger(__name__)


@lru_cache
def get_vector_store() -> QdrantVectorStore:
    """Get or create the QdrantVectorStore singleton."""
    logger.info("Initializing QdrantVectorStore...")
    return QdrantVectorStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        embedding_api_key=settings.google_api_key,
    )


@lru_cache
def get_retriever() -> F1Retriever:
    """Get or create the F1Retriever singleton."""
    logger.info("Initializing F1Retriever...")
    vector_store = get_vector_store()
    # Disable reranker for cross-platform compatibility (torch has issues on Windows)
    # In production Docker/Linux, this can be enabled for better accuracy
    return F1Retriever(vector_store, use_reranker=False)


@lru_cache
def get_llm_client() -> GeminiClient:
    """Get or create the GeminiClient singleton."""
    logger.info("Initializing GeminiClient...")
    return GeminiClient(
        api_key=settings.google_api_key,
        model=settings.llm_model,
    )


@lru_cache
def get_agent() -> F1Agent:
    """Get or create the F1Agent singleton."""
    logger.info("Initializing F1Agent...")
    retriever = get_retriever()
    llm_client = get_llm_client()
    return F1Agent(retriever=retriever, llm_client=llm_client)
