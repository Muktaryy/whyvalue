from unittest.mock import MagicMock, patch
import pytest
import requests
import whyvalue as why
from whyvalue.adapters.http_adapter import TrackedResponse, sanitize_url
from whyvalue.adapters.python_dict import TrackedDict
from whyvalue.adapters.python_list import TrackedList
from whyvalue.history import history


def create_mock_response(
    status_code=200,
    json_data=None,
    text="{}",
    headers=None,
    url="https://api.example.com/users",
):
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = status_code
    mock_resp.url = url
    mock_resp.headers = headers or {"Content-Type": "application/json"}
    mock_resp.text = text
    mock_resp.content = text.encode("utf-8")

    if json_data is not None:
        mock_resp.json.return_value = json_data
    else:
        mock_resp.json.side_effect = ValueError("Invalid JSON")

    return mock_resp


def test_sanitize_url():
    assert (
        sanitize_url("https://api.example.com/users") == "https://api.example.com/users"
    )
    assert (
        sanitize_url("https://api.example.com/users?api_key=SECRET&page=2")
        == "https://api.example.com/users?api_key=REDACTED&page=REDACTED"
    )
    assert (
        sanitize_url("https://api.example.com/data?token=XYZ123")
        == "https://api.example.com/data?token=REDACTED"
    )


def test_get_outside_watch_session_raises():
    with pytest.raises(RuntimeError, match="requires an active WhyValue watch session"):
        why.get("https://api.example.com/users")


@patch("requests.get")
def test_get_passes_url_and_kwargs(mock_requests_get):
    mock_resp = create_mock_response()
    mock_requests_get.return_value = mock_resp

    with why.watch():
        response = why.get(
            "https://api.example.com/users",
            headers={"Accept": "application/json"},
            timeout=5,
        )

        mock_requests_get.assert_called_once_with(
            "https://api.example.com/users",
            headers={"Accept": "application/json"},
            timeout=5,
        )
        assert isinstance(response, TrackedResponse)
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert response.text == "{}"


@patch("requests.get")
def test_get_response_methods_and_attributes(mock_requests_get):
    mock_resp = create_mock_response(status_code=200, text="OK")
    mock_requests_get.return_value = mock_resp

    with why.watch():
        response = why.get("https://api.example.com/health")

        assert response.status_code == 200
        assert response.text == "OK"
        assert response.content == b"OK"
        response.raise_for_status()


@patch("requests.get")
def test_get_http_response_event_recorded(mock_requests_get):
    mock_resp = create_mock_response(
        status_code=200, url="https://api.example.com/final_url"
    )
    mock_requests_get.return_value = mock_resp

    with why.watch():
        response = why.get("https://api.example.com/initial_url?secret=KEY")

        events = history.get_all()
        http_events = [e for e in events if e.get("event_type") == "http_response"]

        assert len(http_events) == 1
        meta = http_events[0]["metadata"]
        assert meta["method"] == "GET"
        assert (
            meta["requested_url"]
            == "https://api.example.com/initial_url?secret=REDACTED"
        )
        assert meta["url"] == "https://api.example.com/final_url"
        assert meta["status_code"] == 200
        assert meta["content_type"] == "application/json"

        # Ensure sensitive request headers or params are not leaked in event metadata
        assert "secret=KEY" not in str(meta)
        assert "headers" not in meta


@patch("requests.get")
def test_response_json_root_dict_and_nested_containers(mock_requests_get):
    payload = {
        "users": [
            {"name": "Ali", "age": 21},
            {"name": "Amina", "age": 24},
        ]
    }
    mock_resp = create_mock_response(json_data=payload)
    mock_requests_get.return_value = mock_resp

    with why.watch():
        response = why.get("https://api.example.com/users")
        data = response.json()

        assert isinstance(data, TrackedDict)
        assert isinstance(data["users"], TrackedList)
        assert isinstance(data["users"][0], TrackedDict)
        assert data["users"][0]["name"] == "Ali"

        # Check JSON paths attached
        assert data._whyvalue_source["json_path"] == "$"
        assert data["users"]._whyvalue_source["json_path"] == "$.users"
        assert data["users"][0]._whyvalue_source["json_path"] == "$.users[0]"


@patch("requests.get")
def test_response_json_root_list(mock_requests_get):
    payload = [{"id": 1}, {"id": 2}]
    mock_resp = create_mock_response(json_data=payload)
    mock_requests_get.return_value = mock_resp

    with why.watch():
        response = why.get("https://api.example.com/items")
        data = response.json()

        assert isinstance(data, TrackedList)
        assert len(data) == 2
        assert isinstance(data[0], TrackedDict)
        assert data[0]["id"] == 1


@patch("requests.get")
def test_no_fake_mutation_events_on_json_conversion(mock_requests_get):
    payload = {"key": "val", "list": [1, 2]}
    mock_resp = create_mock_response(json_data=payload)
    mock_requests_get.return_value = mock_resp

    with why.watch():
        response = why.get("https://api.example.com/data")
        _ = response.json()

        events = history.get_all()
        event_types = [e.get("event_type") for e in events]

        assert "dict_setitem" not in event_types
        assert "list_append" not in event_types
        assert "http_json_decoded" in event_types


@patch("requests.get")
def test_explain_http_json_full_mode(mock_requests_get, capsys):
    payload = {"users": [{"name": "Ali", "age": 21}]}
    mock_resp = create_mock_response(
        json_data=payload, url="https://api.example.com/users"
    )
    mock_requests_get.return_value = mock_resp

    with why.watch():
        response = why.get("https://api.example.com/users")
        data = response.json()
        user = data["users"][0]

        why.explain(user, key="name", mode="full")
        captured = capsys.readouterr().out

        assert "Why is name = Ali?" in captured
        assert "Source:" in captured
        assert "GET https://api.example.com/users" in captured
        assert "Format:" in captured
        assert "JSON" in captured
        assert "Status:" in captured
        assert "200" in captured
        assert "Path:" in captured
        assert "$.users[0].name" in captured
        assert "Original:" in captured
        assert "name = Ali" in captured
        assert "Final:" in captured
        assert "name = Ali" in captured


@patch("requests.get")
def test_explain_http_json_short_and_json_modes(mock_requests_get, capsys):
    payload = {"status": "active"}
    mock_resp = create_mock_response(
        json_data=payload, url="https://api.example.com/status"
    )
    mock_requests_get.return_value = mock_resp

    with why.watch():
        response = why.get("https://api.example.com/status")
        data = response.json()

        # short mode
        why.explain(data, key="status", mode="short")
        short_out = capsys.readouterr().out
        assert "from HTTP GET https://api.example.com/status $.status" in short_out

        # json mode
        json_out = why.explain(data, key="status", mode="json")
        assert isinstance(json_out, dict)
        assert json_out["key"] == "status"
        assert json_out["source"]["source_type"] == "http"
        assert json_out["source"]["method"] == "GET"
        assert json_out["source"]["url"] == "https://api.example.com/status"
        assert json_out["source"]["status_code"] == 200
        assert json_out["source"]["json_path"] == "$.status"


@patch("requests.get")
def test_mutation_after_http_json_load(mock_requests_get, capsys):
    payload = {"users": [{"name": "Ali", "age": 21}]}
    mock_resp = create_mock_response(
        json_data=payload, url="https://api.example.com/users"
    )
    mock_requests_get.return_value = mock_resp

    with why.watch(snapshot=True):
        response = why.get("https://api.example.com/users")
        data = response.json()
        user = data["users"][0]

        user["age"] = 22

        why.explain(user, key="age")
        captured = capsys.readouterr().out

        assert "Why is age = 22?" in captured
        assert "Source:" in captured
        assert "GET https://api.example.com/users" in captured
        assert "Status:" in captured
        assert "200" in captured
        assert "Path:" in captured
        assert "$.users[0].age" in captured
        assert "Transformation history:" in captured
        assert "Original: age = 21" in captured
        assert "set age = 22" in captured
        assert "Final:" in captured
        assert "age = 22" in captured


@patch("requests.get")
def test_json_decoding_error_propagation(mock_requests_get):
    mock_resp = create_mock_response(status_code=200, text="Not JSON")
    mock_resp.json.side_effect = ValueError("Expecting value")
    mock_requests_get.return_value = mock_resp

    with why.watch():
        response = why.get("https://api.example.com/invalid")
        with pytest.raises(ValueError, match="Expecting value"):
            response.json()


@patch("requests.get")
def test_requests_get_exception_no_event_recorded(mock_requests_get):
    mock_requests_get.side_effect = requests.exceptions.ConnectionError(
        "Failed to connect"
    )

    with why.watch():
        with pytest.raises(requests.exceptions.ConnectionError):
            why.get("https://api.example.com/down")

        events = history.get_all()
        http_events = [e for e in events if e.get("event_type") == "http_response"]
        assert len(http_events) == 0


@patch("requests.get")
def test_sensitive_headers_and_params_not_in_provenance(mock_requests_get):
    mock_resp = create_mock_response(
        json_data={"user": "Ali"},
        headers={
            "Content-Type": "application/json",
            "Set-Cookie": "session=ABCDEF123456",
        },
    )
    mock_requests_get.return_value = mock_resp

    with why.watch():
        response = why.get(
            "https://api.example.com/profile?access_token=SECRET_TOKEN",
            headers={"Authorization": "Bearer SECRET_BEARER", "Cookie": "user_id=999"},
        )
        _ = response.json()

        events = history.get_all()
        all_events_str = str(events)

        assert "SECRET_TOKEN" not in all_events_str
        assert "SECRET_BEARER" not in all_events_str
        assert "ABCDEF123456" not in all_events_str
        assert "access_token=REDACTED" in all_events_str
