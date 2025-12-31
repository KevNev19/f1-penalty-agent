"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single message in the chat history."""

    role: str = Field(..., description="Role of the message sender (user, agent)")
    content: str = Field(..., description="Content of the message")


class QuestionRequest(BaseModel):
    """Request model for asking a question."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The F1 penalty or regulation question to ask",
        json_schema_extra={
            "example": "Why did Max Verstappen get a penalty at the 2024 Austrian GP?"
        },
    )
    messages: list[ChatMessage] = Field(
        default_factory=list,
        description="Chat history for context",
    )


class SourceInfo(BaseModel):
    """Information about a source document."""

    title: str = Field(..., description="Title or name of the source")
    doc_type: str = Field(..., description="Type of document (regulation, stewards, race_data)")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance score from retrieval")
    excerpt: str | None = Field(None, description="Short excerpt from the source")
    url: str | None = Field(None, description="URL to the source document")


class AnswerResponse(BaseModel):
    """Response model for an answered question."""

    answer: str = Field(..., description="The AI-generated answer")
    sources: list[SourceInfo] = Field(
        default_factory=list,
        description="Sources used to generate the answer",
    )
    question: str = Field(..., description="The original question asked")
    model_used: str = Field(default="gemini-2.0-flash", description="LLM model used")


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Health status")
    version: str = Field(..., description="API version")
    vector_store: str = Field(..., description="Vector store backend status")


class ErrorDetail(BaseModel):
    """Structured error detail information."""

    type: str = Field(..., description="Exception type name")
    code: str = Field(..., description="Error code (e.g., F1_VEC_002)")
    message: str = Field(..., description="Human-readable error message")


class ErrorLocation(BaseModel):
    """Source location where error occurred."""

    class_name: str = Field(..., alias="class", description="Class name or <module>")
    method: str = Field(..., description="Method/function name")
    file: str = Field(..., description="Source file name")
    line: int = Field(..., description="Line number")
    timestamp: str | None = Field(None, description="When the error occurred")

    class Config:
        """Allow population by field name."""

        populate_by_name = True


class ErrorResponse(BaseModel):
    """Response model for structured errors.

    Example:
        {
            "error": {"type": "QdrantConnectionError", "code": "F1_VEC_002", "message": "..."},
            "location": {"class": "QdrantVectorStore", "method": "_get_client", ...},
            "context": {"url": "https://..."},
            "stack_trace": ["Traceback...", ...]  # Only in debug mode
        }
    """

    error: ErrorDetail = Field(..., description="Error details including type, code, and message")
    location: ErrorLocation | None = Field(None, description="Source location of the error")
    context: dict | None = Field(None, description="Additional debugging context")
    cause: dict | None = Field(None, description="Underlying exception that caused this error")
    stack_trace: list[str] | None = Field(None, description="Stack trace (debug mode only)")
