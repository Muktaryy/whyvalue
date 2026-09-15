import copy
import uuid
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
import requests

from .python_dict import TrackedDict
from .python_list import TrackedList
from ..history import history
from ..provenance import ProvenanceEvent


def sanitize_url(url):
    """Sanitize URL by redacting credentials and query parameter values to avoid leaking sensitive parameters."""
    if not url:
        return url
    parsed = urlparse(str(url))

    netloc = parsed.netloc
    if "@" in netloc:
        _, hostport = netloc.split("@", 1)
        netloc = f"REDACTED@{hostport}"

    sanitized_parsed = parsed._replace(netloc=netloc)

    if parsed.query:
        query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
        sanitized_pairs = [(k, "REDACTED") for k, _ in query_pairs]
        sanitized_query = urlencode(sanitized_pairs)
        sanitized_parsed = sanitized_parsed._replace(query=sanitized_query)

    return urlunparse(sanitized_parsed)


def _convert_http_json_node(node, http_info, json_path, is_snapshot):
    """Recursively convert HTTP JSON node into TrackedDict / TrackedList with HTTP + JSON path metadata."""
    if isinstance(node, dict):
        tracked = TrackedDict()
        tracked._whyvalue_source = {
            "source_type": "http",
            "source_format": "JSON",
            "method": http_info["method"],
            "url": http_info["url"],
            "requested_url": http_info["requested_url"],
            "status_code": http_info["status_code"],
            "content_type": http_info["content_type"],
            "json_path": json_path,
        }

        for k, v in node.items():
            child_path = f"$.{k}" if json_path == "$" else f"{json_path}.{k}"
            converted_v = _convert_http_json_node(v, http_info, child_path, is_snapshot)
            super(TrackedDict, tracked).__setitem__(k, converted_v)

        history.add(
            ProvenanceEvent(
                event_type="http_json_decoded",
                object_id=tracked._whyvalue_id,
                after_value=copy.deepcopy(dict(tracked)) if is_snapshot else None,
                inputs={
                    "url": http_info["url"],
                    "json_path": json_path,
                    "initial_value": copy.deepcopy(dict(tracked)),
                },
                metadata={
                    "operation": "http_json_decoded",
                    "source_type": "http",
                    "source_format": "JSON",
                    "method": http_info["method"],
                    "url": http_info["url"],
                    "requested_url": http_info["requested_url"],
                    "status_code": http_info["status_code"],
                    "content_type": http_info["content_type"],
                    "json_path": json_path,
                    "initial_value": copy.deepcopy(dict(tracked)),
                },
            )
        )
        return tracked

    elif isinstance(node, list):
        tracked = TrackedList()
        tracked._whyvalue_source = {
            "source_type": "http",
            "source_format": "JSON",
            "method": http_info["method"],
            "url": http_info["url"],
            "requested_url": http_info["requested_url"],
            "status_code": http_info["status_code"],
            "content_type": http_info["content_type"],
            "json_path": json_path,
        }

        for idx, item in enumerate(node):
            child_path = f"{json_path}[{idx}]"
            converted_item = _convert_http_json_node(
                item, http_info, child_path, is_snapshot
            )
            super(TrackedList, tracked).append(converted_item)

        history.add(
            ProvenanceEvent(
                event_type="http_json_decoded",
                object_id=tracked._whyvalue_id,
                after_value=copy.deepcopy(list(tracked)) if is_snapshot else None,
                inputs={
                    "url": http_info["url"],
                    "json_path": json_path,
                    "initial_value": copy.deepcopy(list(tracked)),
                },
                metadata={
                    "operation": "http_json_decoded",
                    "source_type": "http",
                    "source_format": "JSON",
                    "method": http_info["method"],
                    "url": http_info["url"],
                    "requested_url": http_info["requested_url"],
                    "status_code": http_info["status_code"],
                    "content_type": http_info["content_type"],
                    "json_path": json_path,
                    "initial_value": copy.deepcopy(list(tracked)),
                },
            )
        )
        return tracked

    else:
        return node


class TrackedResponse:
    """Provenance-aware wrapper around requests.Response."""

    def __init__(self, response, requested_url, final_url, is_snapshot=False):
        self._response = response
        self._requested_url = requested_url
        self._final_url = final_url
        self._is_snapshot = is_snapshot
        self._whyvalue_id = str(uuid.uuid4())

    def __getattr__(self, name):
        return getattr(self._response, name)

    @property
    def status_code(self):
        return self._response.status_code

    @property
    def headers(self):
        return self._response.headers

    @property
    def text(self):
        return self._response.text

    @property
    def content(self):
        return self._response.content

    def raise_for_status(self):
        return self._response.raise_for_status()

    def json(self, **kwargs):
        # Calls standard requests.Response.json()
        data = self._response.json(**kwargs)

        http_info = {
            "source_type": "http",
            "source_format": "JSON",
            "method": "GET",
            "url": self._final_url,
            "requested_url": self._requested_url,
            "status_code": self._response.status_code,
            "content_type": self._response.headers.get("Content-Type"),
        }

        return _convert_http_json_node(
            data,
            http_info=http_info,
            json_path="$",
            is_snapshot=self._is_snapshot,
        )


def get(url, **kwargs):
    """Perform HTTP GET request wrapped in WhyValue provenance tracking."""
    from ..core import is_watching, is_snapshot_enabled

    if not is_watching():
        raise RuntimeError("why.get() requires an active WhyValue watch session.")

    # Native requests.get call
    resp = requests.get(url, **kwargs)

    sanitized_req_url = sanitize_url(url)
    sanitized_final_url = sanitize_url(getattr(resp, "url", None) or url)
    is_snapshot = is_snapshot_enabled()

    tracked_resp = TrackedResponse(
        resp,
        requested_url=sanitized_req_url,
        final_url=sanitized_final_url,
        is_snapshot=is_snapshot,
    )

    history.add(
        ProvenanceEvent(
            event_type="http_response",
            object_id=tracked_resp._whyvalue_id,
            metadata={
                "operation": "http_get",
                "method": "GET",
                "url": sanitized_final_url,
                "requested_url": sanitized_req_url,
                "status_code": resp.status_code,
                "content_type": resp.headers.get("Content-Type"),
            },
        )
    )

    return tracked_resp
