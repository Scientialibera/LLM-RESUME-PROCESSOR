from src.pipeline.pii_remover import _pre_redact


def test_pre_redact_removes_common_identifiers() -> None:
    text = "Contact jane.doe@example.com or +1 (416) 555-0123. DOB 1988-04-10."

    result = _pre_redact(text)

    assert "jane.doe@example.com" not in result
    assert "555-0123" not in result
    assert "1988-04-10" not in result
    assert "[EMAIL]" in result
    assert "[PHONE]" in result
    assert "[DATE]" in result
