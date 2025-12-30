"""Chat endpoint for asking F1 penalty questions."""

import logging

from fastapi import APIRouter, HTTPException

from .....core.domain.utils import normalize_text
from ..deps import get_agent
from ..models import AnswerResponse, ErrorResponse, QuestionRequest, SourceInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post(
    "/ask",
    response_model=AnswerResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def ask_question(request: QuestionRequest) -> AnswerResponse:
    """Ask a question about F1 penalties or regulations.

    Args:
        request: The question request containing the user's question.

    Returns:
        AnswerResponse with the AI-generated answer and sources.

    Raises:
        HTTPException: If the question cannot be processed.
    """
    try:
        agent = get_agent()
        normalized_question = normalize_text(request.question)

        # Get response from the agent
        response = agent.ask(normalized_question)

        # Convert sources to SourceInfo objects
        sources = []
        for source in response.sources_used:
            if isinstance(source, str):
                sources.append(
                    SourceInfo(
                        title=source.replace("[Source] ", ""),
                        doc_type="regulation",
                        relevance_score=0.0,
                        excerpt=None,
                    )
                )
            else:
                sources.append(
                    SourceInfo(
                        title=source.get("source", "Unknown"),
                        doc_type=source.get("doc_type", "unknown"),
                        relevance_score=source.get("score", 0.0),
                        excerpt=source.get("excerpt") or "",
                    )
                )

        return AnswerResponse(
            answer=response.answer,
            sources=sources,
            question=normalized_question,
            model_used="gemini-2.0-flash",
        )

    except ValueError as e:
        logger.warning(f"Invalid request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error processing question: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your question. Please try again.",
        )
