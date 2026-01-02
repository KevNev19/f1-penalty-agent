"""Unit tests for AgentService analytics features."""

from unittest.mock import MagicMock, Mock

import pytest

from src.core.domain.agent import QueryType
from src.core.ports.analytics_port import AnalyticsPort
from src.core.ports.llm_port import LLMPort
from src.core.services.agent_service import AgentService
from src.core.services.retrieval_service import RetrievalService


@pytest.mark.unit
def test_classify_analytics_query():
    """Test classification of analytics queries."""
    llm = Mock(spec=LLMPort)
    retriever = Mock(spec=RetrievalService)
    agent = AgentService(llm, retriever)

    analytics_queries = [
        "How many penalties did McLaren get?",
        "Count the penalties for Verstappen",
        "List all penalties in Las Vegas",
        "What are the stats for Red Bull?",
        "Who has the most penalties?",
        "Total penalties for Lando Norris",
    ]

    for query in analytics_queries:
        assert agent.classify_query(query) == QueryType.ANALYTICS

    # These general queries should NOT be classified as analytics
    for query in [
        "Who won the race?",
        "Explain the track limits rule",
        "Why did Lando get a penalty?",  # Implies explanation, not just count
    ]:
        assert agent.classify_query(query) != QueryType.ANALYTICS


@pytest.mark.unit
def test_ask_analytics_flow():
    """Test the ask flow for analytics queries."""
    llm = Mock(spec=LLMPort)
    retriever = Mock(spec=RetrievalService)
    stats_repo = Mock(spec=AnalyticsPort)

    agent = AgentService(llm, retriever, stats_repo)

    # Mock LLM generation for SQL and Answer
    llm.generate.side_effect = [
        "SELECT count(*) FROM penalties WHERE team='McLaren';",  # 1. Generate SQL
        "McLaren received 5 penalties.",  # 2. Generate Final Answer
    ]

    # Mock Repo result
    stats_repo.execute_query.return_value = [(5,)]

    # Mock Retriever context (empty for this test)
    retriever.retrieve.return_value = MagicMock(get_combined_context=lambda **k: "")

    response = agent.ask("How many penalties did McLaren get?")

    # Check SQL generation prompt was called
    assert llm.generate.call_count == 2

    # Check SQL execution
    stats_repo.execute_query.assert_called_with(
        "SELECT count(*) FROM penalties WHERE team='McLaren';"
    )

    # Check response
    assert response.query_type == QueryType.ANALYTICS
    assert response.answer == "McLaren received 5 penalties."


@pytest.mark.unit
def test_analytics_fail_safe():
    """Test that analytics failure handles gracefully."""
    llm = Mock(spec=LLMPort)
    retriever = Mock(spec=RetrievalService)
    stats_repo = Mock(spec=AnalyticsPort)
    agent = AgentService(llm, retriever, stats_repo)

    # Mock SQL generation exception or DB error
    llm.generate.return_value = "SELECT * ..."
    stats_repo.execute_query.side_effect = Exception("DB Error")

    # Mock Retriever (in case it falls back to general search or classification fails)
    retriever.retrieve.return_value = MagicMock(get_combined_context=lambda **k: "")

    # Needs to handle classify_query regex match for "Count penalties"
    # Or fallback to general.

    # Mock Final Answer generation
    # If SQL fails, it calls llm.generate ONCE for the final answer with error in prompt?
    # Or twice?
    # _generate_sql_and_query calls gen (1). catch exception. return string.
    # ask calls gen (2).
    # So side_effect should have 2 values.
    llm.generate.side_effect = [
        "SELECT * ...",
        "Sorry, I cannot access stats.",
    ]  # Reset side_effect

    response = agent.ask("Count penalties")

    assert "Sorry" in response.answer
