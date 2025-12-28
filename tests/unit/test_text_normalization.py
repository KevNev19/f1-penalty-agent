from fastapi.testclient import TestClient

from src.api import deps
from src.api.main import app
from src.api.routers import chat
from src.common.utils import normalize_text
from src.domain.models import Answer, QueryType, SourceCitation


def test_normalize_text_removes_bom_and_collapses_whitespace():
    text = "\ufeffRésumé   café\r\n\r\n\r\na"  # Contains BOM, double spaces, mixed newlines

    normalized = normalize_text(text)

    assert normalized == "Résumé café\n\na"


def test_chat_response_strips_bom_but_keeps_utf8(monkeypatch):
    class FakeService:
        def ask(self, question: str) -> Answer:  # noqa: D401 - simple stub
            return Answer(
                text="\ufeffRésumé café",  # Leading BOM should be removed
                query_type=QueryType.GENERAL,
                sources=[SourceCitation(title="Règlement", doc_type="regulation")],
                context=None,
            )

    fake_service = FakeService()
    monkeypatch.setattr(deps, "get_question_service", lambda: fake_service)
    monkeypatch.setattr(chat, "get_question_service", lambda: fake_service)

    client = TestClient(app)
    response = client.post("/api/v1/ask", json={"question": "Why?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Résumé café"
    assert payload["sources"][0]["title"] == "Règlement"
