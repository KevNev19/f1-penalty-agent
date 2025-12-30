"""Cross-encoder re-ranking for improved retrieval precision.

This module provides a re-ranking layer that uses a cross-encoder model
to re-score search results, significantly improving precision over
embedding-based similarity alone.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

    from ..domain import SearchResult

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Re-ranks search results using a cross-encoder model.

    Cross-encoders jointly encode query-document pairs and produce
    more accurate relevance scores than bi-encoder embeddings alone.

    Uses the MS MARCO MiniLM model which is optimized for passage re-ranking.
    Expected precision improvement: +15-20% over embedding-only retrieval.
    """

    MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(self, model_name: str | None = None):
        """Initialize the reranker.

        Args:
            model_name: Optional custom model name. Defaults to MS MARCO MiniLM.
        """
        self.model_name = model_name or self.MODEL_NAME
        self._model = None  # Lazy load to avoid slow startup

    def _get_model(self) -> "CrossEncoder":
        """Lazy load the cross-encoder model."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder

                logger.debug(f"Loading cross-encoder model: {self.model_name}")
                self._model = CrossEncoder(self.model_name)
                logger.info("Cross-encoder model loaded")
            except ImportError:
                raise ImportError(
                    "Please install sentence-transformers to use cross-encoder re-ranking: "
                    "pip install sentence-transformers"
                )
        return self._model

    def rerank(
        self,
        query: str,
        results: list["SearchResult"],
        top_k: int = 5,
    ) -> list["SearchResult"]:
        """Re-rank search results using the cross-encoder.

        Args:
            query: The original search query.
            results: List of SearchResult objects from initial retrieval.
            top_k: Number of top results to return after re-ranking.

        Returns:
            List of SearchResult objects, re-scored and sorted by relevance.
        """
        if not results:
            return []

        if len(results) <= 1:
            return results[:top_k]

        model = self._get_model()

        # Create query-document pairs for the cross-encoder
        pairs = [(query, result.document.content) for result in results]

        logger.debug(f"Input Results DocIDs: {[r.document.doc_id for r in results]}")

        # Get cross-encoder scores
        scores = model.predict(pairs)
        logger.debug(f"Model Scores: {scores}")

        # Create new results with updated scores
        reranked = []
        for result, new_score in zip(results, scores):
            # Create a new SearchResult with the cross-encoder score
            # Import here to avoid circular dependency
            from ..domain import Document
            from ..domain import SearchResult as SR

            reranked.append(
                SR(
                    document=Document(
                        content=result.document.content,
                        metadata=result.document.metadata,
                        doc_id=result.document.doc_id,
                    ),
                    score=float(new_score),
                )
            )

        # Sort by new scores (descending) and return top_k
        reranked.sort(key=lambda x: x.score, reverse=True)

        logger.debug(
            f"Re-ranked {len(results)} results. "
            f"Top score: {reranked[0].score:.3f} -> {reranked[-1].score:.3f}"
        )

        return reranked[:top_k]

    def is_available(self) -> bool:
        """Check if the cross-encoder model can be loaded.

        Returns:
            True if sentence-transformers is installed and model can load.
        """
        try:
            self._get_model()
            return True
        except ImportError:
            return False
        except Exception as e:
            logger.warning(f"Cross-encoder not available: {e}")
            return False
