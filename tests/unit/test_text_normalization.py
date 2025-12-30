from src.core.domain.utils import normalize_text


def test_normalize_text_removes_bom_and_collapses_whitespace():
    text = "\ufeffRésumé   café\r\n\r\n\r\na"  # Contains BOM, double spaces, mixed newlines

    normalized = normalize_text(text)

    assert normalized == "Résumé café\n\na"
