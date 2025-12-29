"""Chat endpoint for asking F1 penalty questions."""

import logging

from fastapi import APIRouter, HTTPException

from ...common.utils import normalize_text
from ..deps import get_question_service
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
    """Ask a question about F1 penalties or regulations."""

    try:
        ask_service = get_question_service()
        normalized_question = normalize_text(request.question)

        response = ask_service.ask(normalized_question)

        sources = [
            SourceInfo(
                title=normalize_text(source.title),
                doc_type=normalize_text(source.doc_type),
                relevance_score=source.relevance_score or 0.0,
                excerpt=normalize_text(source.excerpt or ""),
            )
            for source in response.sources
        ]

        clean_answer = normalize_text(response.text)

        return AnswerResponse(
            answer=clean_answer,
            sources=sources,
            question=normalized_question,
            model_used=response.model_used or "gemini-2.0-flash",
        )

    except ValueError as e:
        error_msg = normalize_text(str(e)) or "Invalid request"
        logger.warning(f"Invalid request: {error_msg}")
        raise HTTPException(
            status_code=400,
            detail=error_msg,
        )
    except Exception as e:  # noqa: BLE001
        error_msg = normalize_text(str(e))
        logger.exception(f"Error processing question: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your question. Please try again.",
        )
