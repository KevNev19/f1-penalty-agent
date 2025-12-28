"""Composition root wiring adapters to the application service."""

from __future__ import annotations

import logging
from functools import lru_cache

from ..adapters.llm.gemini_llm import GeminiLLMAdapter
from ..adapters.retrieval.retriever_adapter import RetrieverAdapter
from ..application.services.ask_question import AskQuestionService
from ..common.rate_limiter import RateLimiter
from ..config import settings
from ..domain.services.prompt_builder import PromptBuilder
from ..domain.services.query_classifier import QueryClassifier
from ..llm.gemini_client import GeminiClient
from ..rag.qdrant_store import QdrantVectorStore
from ..rag.retriever import F1Retriever

logger = logging.getLogger(__name__)


@lru_cache
def get_vector_store() -> QdrantVectorStore:
    logger.info("Initializing QdrantVectorStore (composition root)...")
    embedding_rate_limiter = RateLimiter(settings.embedding_requests_per_minute)
    return QdrantVectorStore(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
        embedding_api_key=settings.google_api_key,
        embedding_rate_limiter=embedding_rate_limiter,
    )


@lru_cache
def get_retriever() -> RetrieverAdapter:
    logger.info("Initializing RetrieverAdapter...")
    vector_store = get_vector_store()
    retriever = F1Retriever(vector_store, use_reranker=True)
    return RetrieverAdapter(retriever)


@lru_cache
def get_llm() -> GeminiLLMAdapter:
    logger.info("Initializing GeminiLLMAdapter...")
    llm_rate_limiter = RateLimiter(settings.llm_requests_per_minute)
    client = GeminiClient(
        api_key=settings.google_api_key,
        model=settings.llm_model,
        rate_limiter=llm_rate_limiter,
    )
    return GeminiLLMAdapter(client)


@lru_cache
def get_ask_service() -> AskQuestionService:
    logger.info("Initializing AskQuestionService...")
    classifier = QueryClassifier()
    prompt_builder = PromptBuilder()
    llm = get_llm()
    retriever = get_retriever()
    return AskQuestionService(classifier, prompt_builder, llm, retriever)
