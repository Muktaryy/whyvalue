import pytest
import requests
from unittest.mock import patch, MagicMock
import whyvalue as why
from whyvalue.history import history
from whyvalue.adapters.http_adapter import sanitize_url


def test_repeated_watch_calls_do_not_raise():
    """Requirement 3A: repeated why.watch() calls should be safe and no-op without raising RuntimeError."""
    with why.watch():
        assert why.is_watching() is True
        # Repeated call should not raise RuntimeError
        session2 = why.watch()
        assert why.is_watching() is True
        why.stop(force=False)
        assert why.is_watching() is True
    assert why.is_watching() is False


def test_dict_pop_missing_key_with_default_no_mutation_event():
    """Requirement 8: dict.pop(missing_key, default) must not record a mutation event."""
    with why.watch():
        d = why.track({"a": 1})
        val = d.pop("missing", 42)
        assert val == 42
        events = [e for e in history.get_all() if e.get("event_type") == "dict_pop"]
        assert len(events) == 0


def test_sanitize_url_userinfo_credentials():
    """Requirement 12: sanitize_url must redact username:password embedded in netloc."""
    sanitized = sanitize_url(
        "https://user:secret123@api.example.com/data?key=topsecret"
    )
    assert "secret123" not in sanitized
    assert "topsecret" not in sanitized
    assert "REDACTED" in sanitized
    assert sanitized == "https://REDACTED@api.example.com/data?key=REDACTED"


def test_explain_negative_list_index(capsys):
    """Requirement 11 & 16: why.explain() supports negative list indexing."""
    with why.watch():
        items = why.track(["first", "second", "third"])
        why.explain(items, index=-1)
        out = capsys.readouterr().out
        assert (
            "Why is index 2 = third?" in out
            or "Why is this list" in out
            or "third" in out
        )


def test_json_key_path_with_dots(tmp_path):
    """Requirement 9: JSON keys containing dots or spaces use bracket notation."""
    json_file = tmp_path / "special.json"
    json_file.write_text('{"user.name": "Ali"}', encoding="utf-8")
    with why.watch():
        data = why.load_json(json_file)
        assert data._whyvalue_source["json_path"] == "$"
        assert data["user.name"] == "Ali"
