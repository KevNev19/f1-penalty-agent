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
