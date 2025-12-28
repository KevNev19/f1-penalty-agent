from fastapi.testclient import TestClient

from src.agent.f1_agent import AgentResponse, QueryType
from src.api import deps
from src.api.main import app
from src.api.routers import chat
from src.common.utils import normalize_text


def test_normalize_text_removes_bom_and_collapses_whitespace():
    text = "\ufeffRésumé   café\r\n\r\n\r\na"  # Contains BOM, double spaces, mixed newlines

    normalized = normalize_text(text)

    assert normalized == "Résumé café\n\na"


def test_chat_response_strips_bom_but_keeps_utf8(monkeypatch):
    class FakeAgent:
        def ask(self, question: str) -> AgentResponse:  # noqa: D401 - simple stub
            return AgentResponse(
                answer="\ufeffRésumé café",  # Leading BOM should be removed
                query_type=QueryType.GENERAL,
                sources_used=["[Source] Règlement"],
                context=None,
            )

    fake_agent = FakeAgent()
    monkeypatch.setattr(deps, "get_agent", lambda: fake_agent)
    monkeypatch.setattr(chat, "get_agent", lambda: fake_agent)

    client = TestClient(app)
    response = client.post("/api/v1/ask", json={"question": "Why?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Résumé café"
    assert payload["sources"][0]["title"] == "Règlement"
