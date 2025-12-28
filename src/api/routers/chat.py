"""Chat endpoint for asking F1 penalty questions."""

import logging

from fastapi import APIRouter, HTTPException

from ...common.utils import clean_text
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

        # Clean the incoming question once at the boundary
        normalized_question = clean_text(request.question)

        # Get response from the agent
        response = agent.ask(normalized_question)

        # Convert sources to SourceInfo objects
        # Sanitize ALL text fields to prevent BOM encoding errors in JSON response
        sources = []
        for source in response.sources_used:
            # Handle both string and dict formats
            if isinstance(source, str):
                sources.append(
                    SourceInfo(
                        title=clean_text(source.replace("[Source] ", ""), ascii_only=True),
                        doc_type="regulation",
                        relevance_score=0.0,
                        excerpt=None,
                    )
                )
            else:
                sources.append(
                    SourceInfo(
                        title=clean_text(source.get("source", "Unknown"), ascii_only=True),
                        doc_type=clean_text(source.get("doc_type", "unknown"), ascii_only=True),
                        relevance_score=source.get("score", 0.0),
                        excerpt=clean_text(source.get("excerpt") or "", ascii_only=True),
                    )
                )

        # Clean the answer once before returning
        clean_answer = clean_text(response.answer, ascii_only=True)

        return AnswerResponse(
            answer=clean_answer,
            sources=sources,
            question=clean_text(normalized_question, ascii_only=True),
            model_used="gemini-2.0-flash",
        )

    except ValueError as e:
        error_msg = clean_text(str(e), ascii_only=True) or "Invalid request"
        logger.warning(f"Invalid request: {error_msg}")
        raise HTTPException(
            status_code=400,
            detail=error_msg,
        )
    except Exception as e:
        error_msg = clean_text(str(e), ascii_only=True)
        logger.exception(f"Error processing question: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your question. Please try again.",
        )
