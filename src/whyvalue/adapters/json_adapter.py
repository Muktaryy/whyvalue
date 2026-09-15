import copy
import json
from pathlib import Path

from .python_dict import TrackedDict
from .python_list import TrackedList
from ..history import history
from ..provenance import ProvenanceEvent


def _format_key_path(base_path, key):
    str_k = str(key)
    if str_k.isidentifier() and "." not in str_k:
        return f"$.{str_k}" if base_path == "$" else f"{base_path}.{str_k}"
    escaped = str_k.replace('"', '\\"')
    return f'$["{escaped}"]' if base_path == "$" else f'{base_path}["{escaped}"]'


def _convert_json_node(node, source_path, json_path, is_snapshot):
    """Recursively convert parsed JSON data into tracked containers with JSON path metadata."""
    if isinstance(node, dict):
        tracked = TrackedDict()
        tracked._whyvalue_source = {
            "source_type": "json",
            "source_path": str(source_path),
            "json_path": json_path,
        }

        for k, v in node.items():
            child_path = _format_key_path(json_path, k)
            converted_v = _convert_json_node(v, source_path, child_path, is_snapshot)
            super(TrackedDict, tracked).__setitem__(k, converted_v)

        history.add(
            ProvenanceEvent(
                event_type="json_loaded",
                object_id=tracked._whyvalue_id,
                after_value=copy.deepcopy(dict(tracked)) if is_snapshot else None,
                inputs={
                    "source_path": str(source_path),
                    "json_path": json_path,
                    "initial_value": copy.deepcopy(dict(tracked)),
                },
                metadata={
                    "operation": "json_loaded",
                    "source_type": "json",
                    "source_path": str(source_path),
                    "json_path": json_path,
                    "initial_value": copy.deepcopy(dict(tracked)),
                },
            )
        )
        return tracked

    elif isinstance(node, list):
        tracked = TrackedList()
        tracked._whyvalue_source = {
            "source_type": "json",
            "source_path": str(source_path),
            "json_path": json_path,
        }

        for idx, item in enumerate(node):
            child_path = f"{json_path}[{idx}]"
            converted_item = _convert_json_node(
                item, source_path, child_path, is_snapshot
            )
            super(TrackedList, tracked).append(converted_item)

        history.add(
            ProvenanceEvent(
                event_type="json_loaded",
                object_id=tracked._whyvalue_id,
                after_value=copy.deepcopy(list(tracked)) if is_snapshot else None,
                inputs={
                    "source_path": str(source_path),
                    "json_path": json_path,
                    "initial_value": copy.deepcopy(list(tracked)),
                },
                metadata={
                    "operation": "json_loaded",
                    "source_type": "json",
                    "source_path": str(source_path),
                    "json_path": json_path,
                    "initial_value": copy.deepcopy(list(tracked)),
                },
            )
        )
        return tracked

    else:
        return node


def load_json(path, encoding="utf-8"):
    """Load JSON from a file path into WhyValue tracked containers."""
    from ..core import is_watching, is_snapshot_enabled

    if not is_watching():
        raise RuntimeError("why.load_json() requires an active WhyValue watch session.")

    file_path = Path(path)
    with open(file_path, mode="r", encoding=encoding) as f:
        parsed_data = json.load(f)

    is_snapshot = is_snapshot_enabled()
    tracked_root = _convert_json_node(
        parsed_data,
        source_path=str(path),
        json_path="$",
        is_snapshot=is_snapshot,
    )

    return tracked_root
