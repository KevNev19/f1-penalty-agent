import logging
from functools import lru_cache

from ..application.services.ask_question import AskQuestionService
from ..composition.container import (
    get_ask_service as _get_ask_service,
    get_llm as _get_llm,
    get_retriever as _get_retriever,
    get_vector_store as _get_vector_store,
)
from ..ports.llm import LLMPort
from ..ports.retrieval import RetrievalPort
from ..rag.qdrant_store import QdrantVectorStore

logger = logging.getLogger(__name__)


@lru_cache
def get_vector_store() -> QdrantVectorStore:
    logger.info("Delegating to composition root for vector store...")
    return _get_vector_store()


@lru_cache
def get_retriever() -> RetrievalPort:
    logger.info("Delegating to composition root for retriever...")
    return _get_retriever()


@lru_cache
def get_llm_client() -> LLMPort:
    logger.info("Delegating to composition root for llm...")
    return _get_llm()


@lru_cache
def get_question_service() -> AskQuestionService:
    logger.info("Delegating to composition root for ask service...")
    return _get_ask_service()
