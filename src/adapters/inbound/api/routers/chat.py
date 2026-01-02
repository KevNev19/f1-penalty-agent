"""Chat endpoint for asking F1 penalty questions."""

import logging

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from .....core.domain.agent import ChatMessage as DomainChatMessage
from .....core.domain.utils import normalize_text
from ..deps import get_agent
from ..models import AnswerResponse, ErrorResponse, QuestionRequest, SourceInfo

logger = logging.getLogger(__name__)

# Rate limiter for chat endpoints - more restrictive than general API
# 20 requests per minute per IP to prevent abuse of LLM resources
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.post(
    "/ask",
    response_model=AnswerResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
@limiter.limit("20/minute")
def ask_question(request: Request, body: QuestionRequest) -> AnswerResponse:
    """Ask a question about F1 penalties or regulations.

    Args:
        request: The FastAPI request object (used for rate limiting).
        body: The question request containing the user's question.

    Returns:
        AnswerResponse with the AI-generated answer and sources.

    Raises:
        HTTPException: If the question cannot be processed.
    """
    try:
        agent = get_agent()
        normalized_question = normalize_text(body.question)

        # Validate minimum input length for meaningful processing
        if len(normalized_question.strip()) < 3:
            return AnswerResponse(
                answer="I need a bit more context to help you. Could you ask about a specific F1 penalty, regulation, or race incident?",
                sources=[],
                question=normalized_question,
                model_used="gemini-2.0-flash",
            )

        # Convert API messages to Domain messages
        history = [DomainChatMessage(role=m.role, content=m.content) for m in body.messages]

        # Get response from the agent
        response = agent.ask(normalized_question, messages=history)

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
                        url=source.get("url"),
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


@router.post("/ask/stream")
@limiter.limit("20/minute")
def ask_question_stream(request: Request, body: QuestionRequest):
    """Stream the response token-by-token using Server-Sent Events.

    Args:
        request: The FastAPI request object (used for rate limiting).
        body: The question request containing the user's question.

    Returns:
        StreamingResponse with SSE-formatted chunks.
    """
    import json

    from fastapi.responses import StreamingResponse

    def generate():
        try:
            agent = get_agent()
            normalized_question = normalize_text(body.question)

            # Validate minimum input length
            if len(normalized_question.strip()) < 3:
                yield f"data: {json.dumps({'type': 'chunk', 'content': 'I need a bit more context to help you.'})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'sources': []})}\n\n"
                return

            # Stream the response chunks
            full_response = ""
            for chunk in agent.ask_stream(normalized_question):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"

            # Send done signal with sources (empty for now, could be enhanced)
            yield f"data: {json.dumps({'type': 'done', 'sources': []})}\n\n"

        except ValueError as e:
            logger.warning(f"Invalid streaming request: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        except Exception as e:
            logger.exception(f"Error in streaming response: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'An error occurred. Please try again.'})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
