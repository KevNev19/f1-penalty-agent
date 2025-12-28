"""Chat endpoint for asking F1 penalty questions."""

import logging

from fastapi import APIRouter, HTTPException

from ...common.utils import sanitize_text
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

        # Get response from the agent
        response = agent.ask(request.question)

        # Convert sources to SourceInfo objects
        # Sanitize ALL text fields to prevent BOM encoding errors in JSON response
        sources = []
        for source in response.sources_used:
            # Handle both string and dict formats
            if isinstance(source, str):
                sources.append(
                    SourceInfo(
                        title=sanitize_text(source.replace("[Source] ", "")),
                        doc_type="regulation",
                        relevance_score=0.0,
                        excerpt=None,
                    )
                )
            else:
                sources.append(
                    SourceInfo(
                        title=sanitize_text(source.get("source", "Unknown")),
                        doc_type=sanitize_text(source.get("doc_type", "unknown")),
                        relevance_score=source.get("score", 0.0),
                        excerpt=sanitize_text(source.get("excerpt") or ""),
                    )
                )

        # Sanitize the answer to remove any BOM or non-ASCII characters
        clean_answer = sanitize_text(response.answer)

        return AnswerResponse(
            answer=clean_answer,
            sources=sources,
            question=sanitize_text(request.question),
            model_used="gemini-2.0-flash",
        )

    except ValueError as e:
        # Sanitize error message to remove BOM and non-ASCII chars
        error_msg = sanitize_text(str(e)) or "Invalid request"
        logger.warning(f"Invalid request: {error_msg}")
        raise HTTPException(
            status_code=400,
            detail=error_msg,
        )
    except Exception as e:
        # Sanitize error message for logging
        error_msg = sanitize_text(str(e))
        logger.exception(f"Error processing question: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your question. Please try again.",
        )
