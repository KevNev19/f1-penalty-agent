"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field


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


class SourceInfo(BaseModel):
    """Information about a source document."""

    title: str = Field(..., description="Title or name of the source")
    doc_type: str = Field(..., description="Type of document (regulation, stewards, race_data)")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance score from retrieval")
    excerpt: str | None = Field(None, description="Short excerpt from the source")


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


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str = Field(..., description="Error message")
    detail: str | None = Field(None, description="Additional error details")
