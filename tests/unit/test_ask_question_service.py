"""Tests for AskQuestionService orchestration and domain context handling."""

from unittest.mock import MagicMock

from src.application.services.ask_question import AskQuestionService
from src.domain.models import DocumentSnippet, QueryType, RetrievalContext


def test_retrieval_context_normalizes_text():
    """Combined context should sanitize whitespace and BOM markers."""

    context = RetrievalContext(
        regulations=[
            DocumentSnippet(
                content="\ufeffArticle 33.3  \n Track limits must be respected.  ",
                metadata={"source": "  FIA Sporting Regulations  "},
            )
        ],
        stewards_decisions=[
            DocumentSnippet(
                content="\r\nUnfair advantage gained.\n\n", metadata={"event": "  Monaco GP  "}
            )
        ],
        race_data=[
            DocumentSnippet(
                content="   Safety Car Deployed   \r\n", metadata={"race": "Monaco Grand Prix"}
            )
        ],
        query="Why was the driver penalized?",
    )

    combined = context.get_combined_context()

    assert "=== FIA REGULATIONS ===" in combined
    assert "[Source: FIA Sporting Regulations]" in combined
    assert "Article 33.3" in combined  # BOM removed and whitespace normalized
    assert "[Event: Monaco GP]" in combined
    assert "Safety Car Deployed" in combined


def test_ask_question_service_delegates_and_builds_sources():
    """Service should orchestrate classifier, retrieval, prompting, and LLM calls."""

    classifier = MagicMock()
    classifier.classify.return_value = QueryType.RULE_LOOKUP

    prompt_builder = MagicMock()
    prompt_builder.build.return_value = ("prompt", "system-prompt")

    llm = MagicMock()
    llm.generate.return_value = "final answer"

    retriever = MagicMock()
    retriever.extract_race_context.return_value = {"race": "Monaco"}
    retriever.retrieve.return_value = RetrievalContext(
        regulations=[DocumentSnippet(content="reg text", metadata={"source": "regs"})],
        stewards_decisions=[
            DocumentSnippet(content="sd", metadata={"event": "Monaco", "source": "SD"})
        ],
        race_data=[
            DocumentSnippet(content="rc", metadata={"race": "Monaco Grand Prix", "season": 2024})
        ],
        query="original",
    )

    service = AskQuestionService(classifier, prompt_builder, llm, retriever)

    answer = service.ask("  Why was the driver penalized?  ")

    classifier.classify.assert_called_once()
    prompt_builder.build.assert_called_once()
    llm.generate.assert_called_once_with("prompt", system_prompt="system-prompt")

    # Retrieval invoked with normalized query and extracted context
    retriever.extract_race_context.assert_called_once_with("Why was the driver penalized?")
    retriever.retrieve.assert_called_once()

    assert answer.text == "final answer"
    assert answer.query_type == QueryType.RULE_LOOKUP
    # Sources should reflect all three retrieval buckets without duplicates
    assert {s.title for s in answer.sources} == {
        "regs",
        "SD (Monaco)",
        "Monaco Grand Prix 2024",
    }
