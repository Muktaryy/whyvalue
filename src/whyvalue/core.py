import copy
import pandas as pd

from .history import history
from .provenance import ProvenanceEvent
from .adapters import pandas as pandas_adapter
from .adapters.python_list import TrackedList
from .adapters.python_dict import TrackedDict
from .adapters.json_adapter import load_json
from .adapters.csv_adapter import load_csv
from .adapters.txt_adapter import load_txt
from .adapters.http_adapter import get
from .adapters.pandas import to_dataframe


_watching = False
_snapshot_enabled = False


def _get_dataframe_source_meta(df, row=None, column=None):
    """Retrieve upstream source metadata for a DataFrame or Series created via why.to_dataframe()."""
    attrs = getattr(df, "attrs", {})
    source_info = attrs.get("_whyvalue_source")

    if not source_info:
        df_id = attrs.get("_whyvalue_id")
        if df_id:
            for event in reversed(history.get_all()):
                if event.get("event_type") == "to_dataframe" and (
                    event.get("dataframe_id") == df_id
                    or event.get("object_id") == df_id
                ):
                    source_info = event.get("metadata", {}).get("source_metadata")
                    break

    if not source_info:
        return None

    s_type = source_info.get("source_type", "").lower()
    s_path = source_info.get("source_path")

    if s_type == "csv":
        res = {
            "source_type": "csv",
            "source_format": "CSV",
            "source_path": s_path,
        }
        if row is not None:
            res["csv_row"] = (row + 1) if isinstance(row, int) else row
        if column is not None:
            res["csv_column"] = column
        return res

    if s_type == "json":
        base_path = source_info.get("json_path", "$")
        res = {
            "source_type": "json",
            "source_format": "JSON",
            "source_path": s_path,
        }
        if row is not None and column is not None:
            if base_path == "$":
                res["json_path"] = f"$[{row}].{column}"
            else:
                res["json_path"] = f"{base_path}[{row}].{column}"
        elif base_path:
            res["json_path"] = base_path
        return res

    if s_type == "http":
        base_path = source_info.get("json_path", "$")
        res = {
            "source_type": "http",
            "source_format": "JSON",
            "method": source_info.get("method", "GET"),
            "url": source_info.get("url"),
            "requested_url": source_info.get("requested_url"),
            "status_code": source_info.get("status_code"),
            "content_type": source_info.get("content_type"),
        }
        if row is not None and column is not None:
            if base_path == "$":
                res["json_path"] = f"$[{row}].{column}"
            else:
                res["json_path"] = f"{base_path}[{row}].{column}"
        elif base_path:
            res["json_path"] = base_path
        return res

    if s_type in ("list", "dict", "track"):
        return {
            "source_type": s_type,
            "source_format": "Python object",
        }

    return {
        "source_type": s_type,
        "source_format": source_info.get("source_format", "Unknown"),
        "source_path": s_path,
    }


def _get_source_metadata(obj, key=None):
    """Retrieve source metadata (source_type, source_path, json_path, csv_row, csv_column, line_count, line, url, method, status_code) if available on tracked object."""
    source_info = getattr(obj, "_whyvalue_source", None)
    if not source_info:
        return None

    s_type = source_info.get("source_type", "json").lower()
    s_path = source_info.get("source_path")

    if s_type == "csv":
        csv_row = source_info.get("csv_row")
        res = {
            "source_type": "csv",
            "source_format": "CSV",
            "source_path": s_path,
        }
        if csv_row is not None:
            res["csv_row"] = csv_row
        if key is not None:
            res["csv_column"] = key
        return res

    if s_type == "txt":
        res = {
            "source_type": "txt",
            "source_format": "TXT",
            "source_path": s_path,
            "line_count": source_info.get("line_count"),
        }
        if key is not None:
            res["line"] = key + 1 if isinstance(key, int) else key
        return res

    if s_type == "http":
        base_path = source_info.get("json_path", "$")
        if key is not None:
            if base_path == "$":
                full_json_path = f"$.{key}"
            else:
                full_json_path = f"{base_path}.{key}"
        else:
            full_json_path = base_path

        return {
            "source_type": "http",
            "source_format": "JSON",
            "method": source_info.get("method", "GET"),
            "url": source_info.get("url"),
            "requested_url": source_info.get("requested_url"),
            "status_code": source_info.get("status_code"),
            "content_type": source_info.get("content_type"),
            "json_path": full_json_path,
        }

    base_path = source_info.get("json_path", "$")
    if key is not None:
        if base_path == "$":
            full_json_path = f"$.{key}"
        else:
            full_json_path = f"{base_path}.{key}"
    else:
        full_json_path = base_path

    return {
        "source_type": "json",
        "source_format": "JSON",
        "source_path": s_path,
        "json_path": full_json_path,
    }


def track(obj):
    """Track a Python object (lists or dicts) for provenance."""
    if not is_watching():
        raise RuntimeError("why.track() requires an active WhyValue watch session.")

    if isinstance(obj, list):
        tracked = TrackedList(obj)
        initial_snapshot = copy.deepcopy(list(tracked))

        history.add(
            ProvenanceEvent(
                event_type="list_created",
                object_id=tracked._whyvalue_id,
                after_value=initial_snapshot,
                inputs={"initial_value": initial_snapshot},
                metadata={"operation": "created", "initial_value": initial_snapshot},
            )
        )

        return tracked

    if isinstance(obj, dict):
        tracked = TrackedDict(obj)
        initial_snapshot = copy.deepcopy(dict(tracked))

        history.add(
            ProvenanceEvent(
                event_type="dict_created",
                object_id=tracked._whyvalue_id,
                after_value=initial_snapshot,
                inputs={"initial_value": initial_snapshot},
                metadata={"operation": "created", "initial_value": initial_snapshot},
            )
        )

        return tracked

    raise TypeError("WhyValue tracking does not support this object type yet.")


class WatchSession:
    """Context manager for WhyValue tracking session."""

    def __init__(self, snapshot=False):
        self.snapshot = snapshot

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if is_watching():
            stop(force=False)
        return False


def watch(snapshot=False):
    """Start WhyValue tracking."""
    global _watching, _snapshot_enabled, _watch_depth

    if _watching:
        if snapshot and not _snapshot_enabled:
            _snapshot_enabled = True
            pandas_adapter.enable(snapshot=True)
        _watch_depth += 1
        print("WhyValue is already watching.")
        return WatchSession(snapshot=_snapshot_enabled)

    history.clear()
    _snapshot_enabled = bool(snapshot)
    pandas_adapter.enable(snapshot=_snapshot_enabled)

    _watching = True
    _watch_depth = 1

    print("WhyValue is watching your data.")
    return WatchSession(snapshot=_snapshot_enabled)


def stop(force=True):
    """Stop WhyValue tracking."""
    global _watching, _snapshot_enabled, _watch_depth

    if not _watching:
        print("WhyValue is not currently watching.")
        return

    if not force and _watch_depth > 1:
        _watch_depth -= 1
        return

    pandas_adapter.disable()

    _watching = False
    _snapshot_enabled = False
    _watch_depth = 0

    print("WhyValue stopped watching.")


def is_watching():
    """Return whether WhyValue is currently watching."""
    return _watching


def is_snapshot_enabled():
    """Return whether snapshot capture is enabled."""
    return _snapshot_enabled


def _get_symbol(operation):
    symbols = {
        "add": "+",
        "multiply": "×",
        "subtract": "-",
        "divide": "/",
    }

    return symbols.get(operation, "?")


def _get_dataframe_id(obj):
    """Return the WhyValue lineage ID stored on a DataFrame or Series."""
    if not hasattr(obj, "attrs"):
        return None

    return obj.attrs.get("_whyvalue_id") or obj.attrs.get("_whyvalue_dataframe_id")


def _event_matches_dataframe(event, dataframe_id):
    """Return whether an event belongs to a DataFrame lineage."""
    if dataframe_id is None:
        return False

    return event.get("dataframe_id") == dataframe_id


def _find_event(obj, column):
    """Find the most recent transformation for a column."""
    dataframe_id = _get_dataframe_id(obj)
    events = history.get_all()

    for event in reversed(events):
        if (
            _event_matches_dataframe(event, dataframe_id)
            and (
                event.get("column") == column
                or (event["type"] == "rename" and column in event["columns"].values())
                or event["type"] == "merge"
                or (event["type"] == "groupby" and event.get("source") == column)
            )
            and event["type"] != "filter"
        ):
            return event

    return None


def _find_events_by_dataframe_id(dataframe_id, column):
    """Find all matching events for a dataframe ID + column in chronological order."""
    if dataframe_id is None:
        return []

    events = history.get_all()
    matching = []

    for event in events:
        if (
            _event_matches_dataframe(event, dataframe_id)
            and (
                event.get("column") == column
                or (event["type"] == "rename" and column in event["columns"].values())
                or event["type"] == "merge"
                or (event["type"] == "groupby" and event.get("source") == column)
            )
            and event["type"] != "filter"
        ):
            matching.append(event)

    return matching


def _find_events(obj, column):
    """Find all transformations for a column in chronological order."""
    return _find_events_by_dataframe_id(_get_dataframe_id(obj), column)


def _find_event_by_type(obj, column, event_type):
    """Find the most recent event of a specific type."""
    dataframe_id = _get_dataframe_id(obj)
    events = history.get_all()

    for event in reversed(events):
        if (
            _event_matches_dataframe(event, dataframe_id)
            and event.get("column") == column
            and event["type"] == event_type
        ):
            return event

    return None


def _find_filter_for_row(row, obj=None):
    """Find the most recent row-removal event."""
    events = history.get_all()

    dataframe_id = None

    if obj is not None:
        dataframe_id = _get_dataframe_id(obj)

    for event in reversed(events):
        if event["type"] not in ("filter", "dropna", "combined_filter"):
            continue

        if not _event_matches_dataframe(
            event,
            dataframe_id,
        ):
            continue

        if row in event["removed_rows"]:
            return event

    return None


def trace(obj):
    """Show transformations belonging to a DataFrame."""
    dataframe_id = _get_dataframe_id(obj)

    events = [
        event
        for event in history.get_all()
        if _event_matches_dataframe(
            event,
            dataframe_id,
        )
    ]

    if not events:
        print("No transformations recorded.")
        return

    print("WhyValue Trace")
    print()

    for event in events:
        ev_type = event.get("event_type", event.get("type"))
        if ev_type == "column_created":
            symbol = _get_symbol(event.get("operation"))

            print(
                f"{event.get('column')} = {event.get('left')} {symbol} {event.get('right')}"
            )

        elif ev_type == "column_filled":
            print(f"{event.get('column')}: missing values → {event.get('value')}")

        elif ev_type == "filter":
            print(
                f"filter: {event.get('column')} {event.get('operator')} {event.get('value')}"
            )


def _explain_column(obj, row, column):
    """Explain one column and recursively explain dependencies."""
    event = _find_event(obj, column)

    if event is None:
        value = obj.loc[row, column] if not isinstance(obj, pd.Series) else obj.loc[row]
        print(f"{column} = {value}")
        return

    if event["type"] == "column_created":
        if event.get("operation") == "copy":
            result_value = (
                obj.loc[row, column] if not isinstance(obj, pd.Series) else obj.loc[row]
            )
            source = event["source"]
            print("Copied from column:")
            print(source)
            print()
            print("Source: another DataFrame")
            print()
            print(f"{column} = {result_value}")
            return

        symbol = _get_symbol(event["operation"])

        left_type = event.get(
            "left_type",
            "column",
        )

        right_type = event.get(
            "right_type",
            "column",
        )

        current_df_id = _get_dataframe_id(obj)

        left_df_id = event.get("left_dataframe_id")
        is_left_local = False
        if left_type == "scalar":
            is_left_local = True
            left_value = event["left"]
        else:
            left_column = event["left"]
            if (
                (left_df_id is None or left_df_id == current_df_id)
                and hasattr(obj, "columns")
                and left_column in obj.columns
            ):
                is_left_local = True
                _explain_column(
                    obj,
                    row,
                    left_column,
                )
                left_value = (
                    obj.loc[row, left_column]
                    if not isinstance(obj, pd.Series)
                    else obj.loc[row]
                )
            else:
                is_left_local = False
                left_value = None

        right_df_id = event.get("right_dataframe_id")
        is_right_local = False
        if right_type == "scalar":
            is_right_local = True
            right_value = event["right"]
        else:
            right_column = event["right"]
            if (
                (right_df_id is None or right_df_id == current_df_id)
                and hasattr(obj, "columns")
                and right_column in obj.columns
            ):
                is_right_local = True
                _explain_column(
                    obj,
                    row,
                    right_column,
                )
                right_value = (
                    obj.loc[row, right_column]
                    if not isinstance(obj, pd.Series)
                    else obj.loc[row]
                )
            else:
                is_right_local = False
                right_value = None

        if left_type == "column" and not is_left_local:
            print(f"{event['left']} came from another DataFrame.")
            print()

        if right_type == "column" and not is_right_local:
            print(f"{event['right']} came from another DataFrame.")
            print()

        result_value = (
            obj.loc[row, column] if not isinstance(obj, pd.Series) else obj.loc[row]
        )

        if is_left_local and is_right_local:
            print()
            print(f"{left_value} {symbol} {right_value}")
            print(f"→ {column} = {result_value}")
        else:
            print("Operation:")
            print(f"{event['left']} {symbol} {event['right']}")
            print()
            print(f"→ {column} = {result_value}")

    elif event["type"] == "column_filled":
        result_value = (
            obj.loc[row, column] if not isinstance(obj, pd.Series) else obj.loc[row]
        )
        fill_value = event["value"]

        if (
            event.get("before_value") is not None
            and event.get("after_value") is not None
        ):
            b_series = event["before_value"]
            a_series = event["after_value"]
            b_val = b_series.loc[row] if hasattr(b_series, "loc") else b_series
            a_val = a_series.loc[row] if hasattr(a_series, "loc") else a_series
            b_str = (
                "NaN" if (isinstance(b_val, float) and pd.isna(b_val)) else str(b_val)
            )
            a_str = (
                "NaN" if (isinstance(a_val, float) and pd.isna(a_val)) else str(a_val)
            )

            print("Original:")
            print(f"{column} = {b_str}")
            print()

            print("Operation:")
            print(f"fillna({fill_value})")
            print()

            print("Before:")
            print(f"{b_str}")
            print()

            print("After:")
            print(f"{a_str}")
            print()

            print("Final:")
            print(f"{column} = {result_value}")

        elif row in event["missing_rows"]:
            print("Original value:")
            print("NaN")
            print()

            print("Transformation:")
            print(f"fillna({fill_value})")
            print()

            print(f"NaN → {result_value}")

        else:
            print(f"{column} = {result_value}")
            print()

            print(f"fillna({fill_value}) did not change this row.")

    elif event["type"] == "astype":
        result_value = obj.loc[row, column]

        print("Transformation:")
        print(f"astype({event['dtype']})")
        print()
        print(f"{event['source']} → {column}")
        print(f"{column} = {result_value}")

    elif event["type"] == "round":
        result_value = obj.loc[row, column]

        print("Transformation:")
        print(f"round({event['decimals']})")
        print()
        print(f"{event['source']} → {column}")
        print(f"{column} = {result_value}")

    elif event["type"] == "rename":
        source = next(
            source
            for source, destination in event["columns"].items()
            if destination == column
        )
        result_value = obj.loc[row, column]

        print("Transformation:")
        print("rename()")
        print()
        print(f"{source} → {column}")
        print(f"{column} = {result_value}")

    elif event["type"] == "map":
        result_value = obj.loc[row, column]

        print("Transformation:")
        print("map()")
        print()
        print("Mapping:")
        for key, value in event["mapping"].items():
            print(f"{key} → {value}")

        print()
        print(f"{event['source']} → {column}")
        print(f"{column} = {result_value}")

    elif event["type"] == "apply":
        result_value = obj.loc[row, column]

        print("Transformation:")
        print(f"apply({event['function']})")
        print()
        print(f"{event['source']} → {column}")
        print(f"{column} = {result_value}")

    elif event["type"] == "merge":
        result_value = obj.loc[row, column]

        how = event.get("how", "inner")
        on = event.get("on")

        if on:
            if isinstance(on, list):
                on_str = ", ".join(on)
            else:
                on_str = str(on)
            merge_desc = f"{how} join on {on_str}"
        else:
            merge_desc = f"{how} join"

        print("Merge:")
        print(merge_desc)
        print()
        print("This DataFrame was created by combining two data sources.")
        print()
        print(f"{column} = {result_value}")

    elif event["type"] == "groupby":
        if isinstance(obj, pd.Series):
            result_value = obj.loc[row]
        else:
            result_value = obj.loc[row, column]

        group_by = event["group_by"]
        aggregation = event["aggregation"]

        source_df_id = event.get("source_dataframe_id")
        source_col = event.get("source")

        source_events = []
        if source_df_id and source_col:
            source_events = _find_events_by_dataframe_id(source_df_id, source_col)

        if source_events:
            print("Source transformation history:")
            print()
            for idx, src_event in enumerate(source_events, start=1):
                print(f"{idx}. {_format_event_summary(src_event)}")

            print()
            print("Aggregation:")
            print(f"{aggregation}()")
            print()
            print("Grouped by:")
            print(f"{group_by} = {row}")
            print()
            print("Final:")
            print(f"{column} = {result_value}")
        else:
            print("Aggregation:")
            print(f"{aggregation}()")
            print()
            print("Grouped by:")
            print(f"{group_by} = {row}")
            print()
            print(f"{column} = {result_value}")


def _format_event_summary(event):
    """Format an event into a single line summary step."""
    event_type = event.get("type")

    if event_type == "column_created":
        op = event.get("operation")
        if op == "copy":
            return f"copy from {event.get('source')}"

        symbol = _get_symbol(op)
        left = event.get("left")
        right = event.get("right")
        col = event.get("column")
        return f"{left} {symbol} {right} → {col}"

    elif event_type == "column_filled":
        return f"fillna({event.get('value')})"

    elif event_type == "astype":
        return f"astype({event.get('dtype')})"

    elif event_type == "round":
        return f"round({event.get('decimals')})"

    elif event_type == "map":
        return "map()"

    elif event_type == "apply":
        return f"apply({event.get('function')})"

    elif event_type == "rename":
        return "rename()"

    elif event_type == "merge":
        return "merge()"

    elif event_type == "groupby":
        return f"{event.get('aggregation')}()"

    return f"{event_type}()"


def _explain_event_chain(obj, row, column, events):
    """Explain a sequence of transformations on the same column."""
    if isinstance(obj, pd.Series):
        result_value = obj.loc[row]
    else:
        result_value = obj.loc[row, column]

    print("Transformation history:")
    print()
    for idx, event in enumerate(events, start=1):
        print(f"{idx}. {_format_event_summary(event)}")

    print()
    print("Final:")
    print(f"{column} = {result_value}")


def _explain_json(obj, row, column, result_value, events):
    """Return a machine-readable dictionary representation of the explanation."""
    steps = []

    for event in events:
        event_type = event["type"]
        if event_type == "column_filled":
            step = {
                "operation": "fillna",
                "value": event.get("value"),
            }
            if (
                event.get("before_value") is not None
                and event.get("after_value") is not None
            ):
                b_series = event["before_value"]
                a_series = event["after_value"]
                b_val = b_series.loc[row] if hasattr(b_series, "loc") else b_series
                a_val = a_series.loc[row] if hasattr(a_series, "loc") else a_series
                step["before"] = (
                    None if (isinstance(b_val, float) and pd.isna(b_val)) else b_val
                )
                step["after"] = (
                    None if (isinstance(a_val, float) and pd.isna(a_val)) else a_val
                )
            elif row in event.get("missing_rows", []):
                step["before"] = None
                step["after"] = event.get("value")

            steps.append(step)

        elif event_type == "column_created":
            step = {
                "operation": event.get("operation", "column_created"),
                "left": event.get("left"),
                "right": event.get("right"),
            }
            steps.append(step)

        else:
            step = {"operation": event_type}
            for k in (
                "value",
                "operator",
                "dtype",
                "decimals",
                "func",
                "source",
                "aggregation",
            ):
                if k in event:
                    step[k] = event[k]
            steps.append(step)

    final_val = (
        None
        if (isinstance(result_value, float) and pd.isna(result_value))
        else result_value
    )

    return {
        "column": column,
        "row": row,
        "final_value": final_val,
        "steps": steps,
    }


def _explain_short(obj, row, column, result_value, events):
    """Return and print a concise summary string."""
    if not events:
        msg = f"{column}: no history"
        print(msg)
        return msg

    short_steps = []
    for event in events:
        event_type = event["type"]
        if event_type == "column_filled":
            fill_val = event.get("value")
            if (
                event.get("before_value") is not None
                and event.get("after_value") is not None
            ):
                b_series = event["before_value"]
                a_series = event["after_value"]
                b_val = b_series.loc[row] if hasattr(b_series, "loc") else b_series
                a_val = a_series.loc[row] if hasattr(a_series, "loc") else a_series
                b_str = (
                    "NaN"
                    if (isinstance(b_val, float) and pd.isna(b_val))
                    else str(b_val)
                )
                a_str = (
                    "NaN"
                    if (isinstance(a_val, float) and pd.isna(a_val))
                    else str(a_val)
                )
                short_steps.append(f"{b_str} → {a_str} via fillna({fill_val})")
            elif row in event.get("missing_rows", []):
                short_steps.append(f"NaN → {fill_val} via fillna({fill_val})")
            else:
                short_steps.append(f"fillna({fill_val}) (no change)")

        elif event_type == "column_created":
            symbol = _get_symbol(event.get("operation"))
            short_steps.append(f"{event.get('left')} {symbol} {event.get('right')}")

        else:
            op_name = event.get("operation", event_type)
            short_steps.append(f"via {op_name}")

    explanation = f"{column}: " + ", ".join(short_steps)
    print(explanation)
    return explanation


def _format_list_event_summary(event):
    """Format a list event into a human-readable step description."""
    event_type = event.get("event_type", event.get("type"))
    metadata = event.get("metadata", {})
    inputs = event.get("inputs", {})

    if event_type == "list_created":
        val = inputs.get("initial_value", metadata.get("initial_value"))
        return f"Created list {val}"

    elif event_type == "list_append":
        val = inputs.get("value", metadata.get("value"))
        return f"append({val})"

    elif event_type == "list_extend":
        vals = inputs.get("iterable", metadata.get("values"))
        return f"extend({vals})"

    elif event_type == "list_insert":
        idx = inputs.get("index", metadata.get("index"))
        val = inputs.get("value", metadata.get("value"))
        return f"insert({idx}, {val})"

    elif event_type == "list_remove":
        val = inputs.get("value", metadata.get("value"))
        return f"remove({val})"

    elif event_type == "list_pop":
        idx = inputs.get("index", metadata.get("index", -1))
        return f"pop({idx})" if idx != -1 else "pop()"

    elif event_type == "list_clear":
        return "clear()"

    elif event_type == "list_setitem":
        idx = inputs.get("index", metadata.get("index"))
        val = inputs.get("value", metadata.get("value"))
        return f"[{idx}] = {val}"

    elif event_type == "list_delitem":
        idx = inputs.get("index", metadata.get("index"))
        return f"del [{idx}]"

    return f"{event_type}()"


def _find_list_events(tracked_list):
    """Find all provenance events for a tracked list in chronological order."""
    obj_id = getattr(tracked_list, "_whyvalue_id", None)
    if obj_id is None:
        return []
    return [
        e
        for e in history.get_all()
        if e.get("object_id") == obj_id or e.get("list_id") == obj_id
    ]


def _explain_list_index(obj, mode, index, events, src_meta):
    """Explain provenance for a specific index in a tracked Python list."""
    obj_id = getattr(obj, "_whyvalue_id", None)

    if isinstance(index, int) and index < 0:
        index = len(obj) + index

    if isinstance(index, int) and 0 <= index < len(obj):
        final_val = obj[index]
    else:
        final_val = None

    line_no = index + 1
    is_txt = src_meta and src_meta.get("source_type") == "txt"

    loaded_event = next(
        (
            e
            for e in events
            if e.get("event_type")
            in ("list_created", "json_loaded", "csv_loaded", "txt_loaded")
        ),
        None,
    )

    original_val = final_val
    if loaded_event:
        init_val = loaded_event.get("inputs", {}).get(
            "initial_value", loaded_event.get("metadata", {}).get("initial_value")
        )
        if (
            init_val is not None
            and isinstance(init_val, list)
            and 0 <= index < len(init_val)
        ):
            original_val = init_val[index]

    user_mutations = [
        e
        for e in events
        if e.get("event_type")
        not in ("list_created", "json_loaded", "csv_loaded", "txt_loaded")
    ]

    if mode == "json":
        steps = []
        for event in user_mutations:
            ev_type = event.get("event_type", event.get("type"))
            op_name = event.get("metadata", {}).get("operation", ev_type)
            step = {
                "event_type": ev_type,
                "operation": op_name,
            }
            if event.get("inputs"):
                step["inputs"] = event["inputs"]
            if event.get("before_value") is not None and isinstance(
                event["before_value"], list
            ):
                if 0 <= index < len(event["before_value"]):
                    step["before"] = event["before_value"][index]
            if event.get("after_value") is not None and isinstance(
                event["after_value"], list
            ):
                if 0 <= index < len(event["after_value"]):
                    step["after"] = event["after_value"][index]
            steps.append(step)

        obj_type = src_meta.get("source_type", "list") if src_meta else "list"
        res = {
            "object_type": obj_type,
            "index": index,
            "final_value": final_val,
            "steps": steps,
        }
        if src_meta:
            s_dict = {
                "source_type": src_meta["source_type"],
                "source_path": src_meta["source_path"],
            }
            if "line" in src_meta:
                s_dict["line"] = src_meta["line"]
            elif "json_path" in src_meta:
                s_dict["json_path"] = src_meta["json_path"]
            res["source"] = s_dict

        return res

    if mode == "short":
        if is_txt:
            source_desc = f"line {line_no}: from TXT {src_meta['source_path']}"
        elif src_meta:
            source_desc = f"index {index}: from {src_meta['source_format']} {src_meta['source_path']}"
        else:
            source_desc = f"index {index}"

        if not user_mutations:
            explanation = f"{source_desc} → final: {final_val}"
        else:
            steps_summary = [_format_list_event_summary(ev) for ev in user_mutations]
            explanation = (
                f"{source_desc}, " + ", ".join(steps_summary) + f" → final: {final_val}"
            )

        print(explanation)
        return explanation

    # mode == "full"
    if is_txt:
        print(f'Why is line {line_no} = "{final_val}"?')
    else:
        print(f"Why is index {index} = {final_val}?")
    print()

    if src_meta:
        print("Source:")
        print(src_meta["source_path"])
        print()
        print("Format:")
        print(src_meta["source_format"])
        print()
        if "line" in src_meta:
            print("Line:")
            print(src_meta["line"])
            print()
        elif "json_path" in src_meta:
            print("Path:")
            print(src_meta["json_path"])
            print()

    if not user_mutations:
        print("Original:")
        if is_txt:
            print(f'"{original_val}"')
        else:
            print(f"{original_val}")
        print()
        print("Final:")
        if is_txt:
            print(f'"{final_val}"')
        else:
            print(f"{final_val}")
        return

    print("Transformation history:")
    print()
    if is_txt:
        print(f'1. Original: "{original_val}"')
    else:
        print(f"1. Original: {original_val}")

    for idx, event in enumerate(user_mutations, start=2):
        summary = _format_list_event_summary(event)
        print(f"{idx}. {summary}")

    print()
    print("Final:")
    if is_txt:
        print(f'"{final_val}"')
    else:
        print(f"{final_val}")


def _explain_list(obj, mode="full", index=None):
    """Explain provenance history for a tracked Python list."""
    events = _find_list_events(obj)
    obj_id = getattr(obj, "_whyvalue_id", None)
    src_meta = _get_source_metadata(obj, key=index)

    if not events and not src_meta:
        if mode == "json":
            res = {
                "object_type": "list",
                "object_id": obj_id,
                "final_value": list(obj),
                "steps": [],
            }
            if index is not None:
                res["index"] = index
            return res
        if mode == "short":
            msg = "list: no history"
            print(msg)
            return msg

        print("No explanation found for list.")
        return None

    if index is not None:
        return _explain_list_index(obj, mode, index, events, src_meta)

    if mode == "json":
        steps = []
        for event in events:
            ev_type = event.get("event_type", event.get("type"))
            op_name = event.get("metadata", {}).get("operation", ev_type)
            step = {
                "event_type": ev_type,
                "operation": op_name,
            }
            if event.get("inputs"):
                step["inputs"] = event["inputs"]
            if event.get("before_value") is not None:
                step["before"] = event["before_value"]
            if event.get("after_value") is not None:
                step["after"] = event["after_value"]
            steps.append(step)

        res = {
            "object_type": "list",
            "object_id": obj_id,
            "final_value": list(obj),
            "steps": steps,
        }
        if src_meta:
            s_dict = {
                "source_type": src_meta["source_type"],
                "source_path": src_meta["source_path"],
            }
            if "line_count" in src_meta:
                s_dict["line_count"] = src_meta["line_count"]
            if "json_path" in src_meta:
                s_dict["json_path"] = src_meta["json_path"]
            res["source"] = s_dict
        return res

    if mode == "short":
        steps_summary = [_format_list_event_summary(ev) for ev in events]
        parts = []
        if src_meta:
            if src_meta["source_type"] == "csv":
                parts.append(f"from CSV {src_meta['source_path']}".strip())
            elif src_meta["source_type"] == "txt":
                parts.append(f"from TXT {src_meta['source_path']}".strip())
            else:
                parts.append(
                    f"from {src_meta['source_format']} {src_meta['source_path']} {src_meta.get('json_path', '$')}"
                )
        parts.extend(steps_summary)
        explanation = "list: " + ", ".join(parts) + f" → final: {list(obj)}"
        print(explanation)
        return explanation

    # mode == "full"
    print(f"Why is this list {list(obj)}?")
    print()

    if src_meta:
        print("Source:")
        print(src_meta["source_path"])
        print()
        print("Format:")
        print(src_meta["source_format"])
        print()
        if "line_count" in src_meta:
            print("Lines:")
            print(src_meta["line_count"])
            print()
        elif "json_path" in src_meta:
            print("Path:")
            print(src_meta["json_path"])
            print()

    user_mutations = [
        e
        for e in events
        if e.get("event_type")
        not in ("list_created", "json_loaded", "csv_loaded", "txt_loaded")
    ]

    if not user_mutations and src_meta:
        print("Original:")
        print(f"{list(obj)}")
        print()
        print("Final:")
        print(f"{list(obj)}")
        return

    print("Transformation history:")
    print()
    for idx, event in enumerate(events, start=1):
        summary = _format_list_event_summary(event)
        print(f"{idx}. {summary}")

    print()
    print("Final:")
    print(f"{list(obj)}")


def _format_dict_event_summary(event, key=None):
    """Format a dict event into a human-readable step description."""
    event_type = event.get("event_type", event.get("type"))
    metadata = event.get("metadata", {})
    inputs = event.get("inputs", {})

    if event_type in ("dict_created", "json_loaded", "csv_loaded", "http_json_decoded"):
        val = inputs.get("initial_value", metadata.get("initial_value", {}))
        if key is not None and isinstance(val, dict) and key in val:
            return f"Original: {key} = {val[key]}"
        if event_type == "dict_created":
            return f"Created dict {val}"
        if event_type == "json_loaded":
            return f"Loaded JSON {inputs.get('source_path', '')}"
        if event_type == "http_json_decoded":
            return f"HTTP {metadata.get('method', 'GET')} {metadata.get('url', '')}"
        return f"Loaded CSV {inputs.get('source_path', '')}"

    elif event_type == "dict_setitem":
        k = inputs.get("key", metadata.get("key"))
        v = inputs.get("value", metadata.get("value"))
        if key is not None:
            return f"set {k} = {v}"
        return f"{k} = {v}"

    elif event_type == "dict_delitem":
        k = inputs.get("key", metadata.get("key"))
        return f"del {k}"

    elif event_type == "dict_update":
        upd = inputs.get("update_dict", metadata.get("update", {}))
        if key is not None and isinstance(upd, dict) and key in upd:
            return f"set {key} = {upd[key]}"
        return f"update({upd})"

    elif event_type == "dict_pop":
        k = inputs.get("key", metadata.get("key"))
        return f"pop({k})"

    elif event_type == "dict_popitem":
        k = inputs.get("key", metadata.get("key"))
        v = inputs.get("value", metadata.get("value"))
        return f"popitem() -> ({k}, {v})"

    elif event_type == "dict_setdefault":
        k = inputs.get("key", metadata.get("key"))
        d = inputs.get("default", metadata.get("default"))
        inserted = inputs.get("inserted", metadata.get("inserted", True))
        if not inserted:
            return f"setdefault({k}, {d}) (existing key)"
        return f"setdefault({k}, {d})"

    elif event_type == "dict_clear":
        return "clear()"

    return f"{event_type}()"


def _find_dict_events(tracked_dict, key=None):
    """Find all provenance events for a tracked dictionary (and optional key) in chronological order."""
    obj_id = getattr(tracked_dict, "_whyvalue_id", None)
    if obj_id is None:
        return []

    events = [
        e
        for e in history.get_all()
        if e.get("object_id") == obj_id or e.get("dict_id") == obj_id
    ]

    if key is None:
        return events

    matching = []
    for e in events:
        ev_type = e.get("event_type", e.get("type"))
        inputs = e.get("inputs", {})
        metadata = e.get("metadata", {})

        if ev_type in (
            "dict_created",
            "json_loaded",
            "csv_loaded",
            "http_json_decoded",
        ):
            initial_map = inputs.get("initial_value", metadata.get("initial_value", {}))
            if isinstance(initial_map, dict) and key in initial_map:
                matching.append(e)

        elif ev_type in (
            "dict_setitem",
            "dict_delitem",
            "dict_pop",
            "dict_popitem",
            "dict_setdefault",
        ):
            if (
                e.get("output") == key
                or inputs.get("key") == key
                or metadata.get("key") == key
            ):
                matching.append(e)

        elif ev_type == "dict_update":
            upd = inputs.get("update_dict", metadata.get("update", {}))
            if isinstance(upd, dict) and key in upd:
                matching.append(e)

        elif ev_type == "dict_clear":
            matching.append(e)

    return matching


def _explain_dict(obj, mode, key=None):
    """Explain provenance history for a tracked Python dictionary."""
    events = _find_dict_events(obj, key=key)
    obj_id = getattr(obj, "_whyvalue_id", None)
    has_key = key is not None and key in obj
    final_val = obj[key] if has_key else (dict(obj) if key is None else None)
    src_meta = _get_source_metadata(obj, key=key)

    if not events and not src_meta:
        if mode == "json":
            res = {
                "object_type": "dict",
                "object_id": obj_id,
                "final_value": final_val,
                "steps": [],
            }
            if key is not None:
                res["key"] = key
            return res

        if mode == "short":
            msg = f"{key}: no history" if key is not None else "dict: no history"
            print(msg)
            return msg

        if key is not None:
            print(f"No explanation found for key '{key}'.")
        else:
            print("No explanation found for dict.")
        return None

    if mode == "json":
        steps = []
        for event in events:
            ev_type = event.get("event_type", event.get("type"))
            op_name = event.get("metadata", {}).get("operation", ev_type)
            step = {
                "event_type": ev_type,
                "operation": op_name,
            }
            if event.get("inputs"):
                step["inputs"] = event["inputs"]

            if event.get("before_value") is not None:
                b_dict = event["before_value"]
                step["before"] = (
                    b_dict.get(key)
                    if (key is not None and isinstance(b_dict, dict))
                    else b_dict
                )
            if event.get("after_value") is not None:
                a_dict = event["after_value"]
                step["after"] = (
                    a_dict.get(key)
                    if (key is not None and isinstance(a_dict, dict))
                    else a_dict
                )

            steps.append(step)

        res = {
            "object_type": "dict",
            "object_id": obj_id,
            "final_value": final_val,
            "steps": steps,
        }
        if key is not None:
            res["key"] = key
        if src_meta:
            s_dict = {
                "source_type": src_meta["source_type"],
            }
            if "source_path" in src_meta and src_meta["source_path"] is not None:
                s_dict["source_path"] = src_meta["source_path"]
            if "method" in src_meta:
                s_dict["method"] = src_meta["method"]
            if "url" in src_meta:
                s_dict["url"] = src_meta["url"]
            if "requested_url" in src_meta:
                s_dict["requested_url"] = src_meta["requested_url"]
            if "status_code" in src_meta:
                s_dict["status_code"] = src_meta["status_code"]
            if "content_type" in src_meta:
                s_dict["content_type"] = src_meta["content_type"]
            if "csv_row" in src_meta:
                s_dict["csv_row"] = src_meta["csv_row"]
            if "csv_column" in src_meta:
                s_dict["csv_column"] = src_meta["csv_column"]
            if "json_path" in src_meta:
                s_dict["json_path"] = src_meta["json_path"]
            res["source"] = s_dict
        return res

    if mode == "short":
        steps_summary = [_format_dict_event_summary(ev, key=key) for ev in events]
        prefix = f"{key}: " if key is not None else "dict: "
        parts = []
        if src_meta:
            if src_meta["source_type"] == "csv":
                row_info = (
                    f" Row {src_meta['csv_row']}" if "csv_row" in src_meta else ""
                )
                col_info = (
                    f" Column {src_meta['csv_column']}"
                    if "csv_column" in src_meta
                    else ""
                )
                parts.append(
                    f"from CSV {src_meta['source_path']}{row_info}{col_info}".strip()
                )
            elif src_meta["source_type"] == "http":
                parts.append(
                    f"from HTTP {src_meta.get('method', 'GET')} {src_meta.get('url', '')} {src_meta.get('json_path', '$')}".strip()
                )
            else:
                parts.append(
                    f"from {src_meta['source_format']} {src_meta['source_path']} {src_meta['json_path']}"
                )
        parts.extend(steps_summary)
        explanation = prefix + ", ".join(parts) + f" → final: {final_val}"
        print(explanation)
        return explanation

    # mode == "full"
    if key is not None:
        print(f"Why is {key} = {final_val}?")
    else:
        print(f"Why is this dict {dict(obj)}?")
    print()

    if src_meta:
        print("Source:")
        if src_meta["source_type"] == "http":
            print(f"{src_meta.get('method', 'GET')} {src_meta.get('url', '')}")
        else:
            print(src_meta["source_path"])
        print()
        print("Format:")
        print(src_meta["source_format"])
        print()
        if "status_code" in src_meta and src_meta["status_code"] is not None:
            print("Status:")
            print(src_meta["status_code"])
            print()
        if "csv_row" in src_meta:
            print("Row:")
            print(src_meta["csv_row"])
            print()
        if "csv_column" in src_meta:
            print("Column:")
            print(src_meta["csv_column"])
            print()
        elif "json_path" in src_meta:
            print("Path:")
            print(src_meta["json_path"])
            print()

    user_mutations = [
        e
        for e in events
        if e.get("event_type")
        not in ("dict_created", "json_loaded", "csv_loaded", "http_json_decoded")
    ]

    if not user_mutations and src_meta:
        print("Original:")
        if key is not None:
            print(f"{key} = {final_val}")
        else:
            print(f"{dict(obj)}")
        print()
        print("Final:")
        if key is not None:
            print(f"{key} = {final_val}")
        else:
            print(f"{dict(obj)}")
        return

    print("Transformation history:")
    print()
    for idx, event in enumerate(events, start=1):
        summary = _format_dict_event_summary(event, key=key)
        print(f"{idx}. {summary}")

    print()
    print("Final:")
    if key is not None:
        print(f"{key} = {final_val}")
    else:
        print(f"{dict(obj)}")


def _explain_json(obj, row, column, result_value, events):
    """Return JSON representation of the explanation."""
    steps = []
    for event in events:
        ev_type = event["type"]
        op_name = event.get("operation", ev_type)
        step = {
            "event_type": ev_type,
            "operation": op_name,
        }
        if event.get("inputs"):
            step["inputs"] = event["inputs"]

        if event.get("before_value") is not None:
            b_series = event["before_value"]
            b_val = b_series.loc[row] if hasattr(b_series, "loc") else b_series
            step["before"] = (
                None if (isinstance(b_val, float) and pd.isna(b_val)) else b_val
            )
        if event.get("after_value") is not None:
            a_series = event["after_value"]
            a_val = a_series.loc[row] if hasattr(a_series, "loc") else a_series
            step["after"] = (
                None if (isinstance(a_val, float) and pd.isna(a_val)) else a_val
            )

        steps.append(step)

    final_val = (
        None
        if (isinstance(result_value, float) and pd.isna(result_value))
        else result_value
    )

    res = {
        "column": column,
        "row": row,
        "final_value": final_val,
        "steps": steps,
    }

    src_meta = _get_dataframe_source_meta(obj, row=row, column=column)
    if src_meta:
        s_dict = {"source_type": src_meta["source_type"]}
        for k in (
            "source_path",
            "method",
            "url",
            "requested_url",
            "status_code",
            "content_type",
            "csv_row",
            "csv_column",
            "json_path",
        ):
            if k in src_meta and src_meta[k] is not None:
                s_dict[k] = src_meta[k]
        res["source"] = s_dict

    return res


def _explain_short(obj, row, column, result_value, events):
    """Return and print a concise summary string."""
    src_meta = _get_dataframe_source_meta(obj, row=row, column=column)

    if not events:
        if src_meta:
            if src_meta["source_type"] == "csv":
                msg = f"{column}: from CSV {src_meta['source_path']} Row {src_meta.get('csv_row', '')} Column {src_meta.get('csv_column', '')} → final: {result_value}".strip()
            elif src_meta["source_type"] == "http":
                msg = f"{column}: from HTTP {src_meta.get('method', 'GET')} {src_meta.get('url', '')} {src_meta.get('json_path', '')} → final: {result_value}".strip()
            elif src_meta["source_type"] == "json":
                msg = f"{column}: from JSON {src_meta.get('source_path', '')} {src_meta.get('json_path', '')} → final: {result_value}".strip()
            else:
                msg = f"{column}: from {src_meta.get('source_format', 'source')} → final: {result_value}"
        else:
            msg = f"{column}: no history"
        print(msg)
        return msg

    short_steps = []
    for event in events:
        event_type = event["type"]
        if event_type == "column_filled":
            fill_val = event.get("value")
            if (
                event.get("before_value") is not None
                and event.get("after_value") is not None
            ):
                b_series = event["before_value"]
                a_series = event["after_value"]
                b_val = b_series.loc[row] if hasattr(b_series, "loc") else b_series
                a_val = a_series.loc[row] if hasattr(a_series, "loc") else a_series
                b_str = (
                    "NaN"
                    if (isinstance(b_val, float) and pd.isna(b_val))
                    else str(b_val)
                )
                a_str = (
                    "NaN"
                    if (isinstance(a_val, float) and pd.isna(a_val))
                    else str(a_val)
                )
                short_steps.append(f"{b_str} → {a_str} via fillna({fill_val})")
            elif row in event.get("missing_rows", []):
                short_steps.append(f"NaN → {fill_val} via fillna({fill_val})")
            else:
                short_steps.append(f"fillna({fill_val}) (no change)")

        elif event_type == "column_created":
            symbol = _get_symbol(event.get("operation"))
            short_steps.append(f"{event.get('left')} {symbol} {event.get('right')}")

        else:
            op_name = event.get("operation", event_type)
            short_steps.append(f"via {op_name}")

    if src_meta:
        if src_meta["source_type"] == "csv":
            src_str = f"from CSV {src_meta['source_path']}"
        elif src_meta["source_type"] == "http":
            src_str = (
                f"from HTTP {src_meta.get('method', 'GET')} {src_meta.get('url', '')}"
            )
        elif src_meta["source_type"] == "json":
            src_str = f"from JSON {src_meta.get('source_path', '')}"
        else:
            src_str = f"from {src_meta.get('source_format', 'source')}"
        explanation = f"{column}: {src_str}, " + ", ".join(short_steps)
    else:
        explanation = f"{column}: " + ", ".join(short_steps)

    print(explanation)
    return explanation


def explain(obj, row=None, column=None, mode=None, key=None, index=None):
    """Explain why a specific cell or tracked object has its current value."""
    if isinstance(obj, TrackedDict) or (
        hasattr(obj, "_whyvalue_id") and isinstance(obj, dict)
    ):
        if (
            key is None
            and isinstance(row, str)
            and row not in ("full", "short", "json")
        ):
            key = row
            row = None

        if mode is None:
            if isinstance(row, str) and row in ("full", "short", "json"):
                mode = row
            else:
                mode = "full"

        if mode not in ("full", "short", "json"):
            raise ValueError("mode must be 'short', 'full', or 'json'")

        return _explain_dict(obj, mode=mode, key=key)

    if (
        isinstance(obj, TrackedList)
        or hasattr(obj, "_whyvalue_id")
        and not isinstance(obj, (pd.DataFrame, pd.Series))
    ):
        if index is None:
            if isinstance(row, int):
                index = row
                row = None
            elif isinstance(key, int):
                index = key
                key = None

        if mode is None:
            if isinstance(row, str) and row in ("full", "short", "json"):
                mode = row
            elif isinstance(column, str) and column in ("full", "short", "json"):
                mode = column
            else:
                mode = "full"

        if mode not in ("full", "short", "json"):
            raise ValueError("mode must be 'short', 'full', or 'json'")

        return _explain_list(obj, mode=mode, index=index)

    if mode is None:
        mode = "full"

    if mode not in ("full", "short", "json"):
        raise ValueError("mode must be 'short', 'full', or 'json'")

    if isinstance(obj, pd.Series) and column is None:
        column = obj.name

    events = _find_events(
        obj,
        column,
    )

    src_meta = _get_dataframe_source_meta(obj, row=row, column=column)

    if not events and not src_meta:
        if mode == "json":
            return {
                "column": column,
                "row": row,
                "final_value": None,
                "steps": [],
            }
        if mode == "short":
            msg = f"{column}: no history"
            print(msg)
            return msg

        print(f"No explanation found for '{column}'.")
        return

    if isinstance(obj, pd.Series):
        result_value = obj.loc[row]
    else:
        result_value = obj.loc[row, column]

    if mode == "json":
        return _explain_json(obj, row, column, result_value, events)

    if mode == "short":
        return _explain_short(obj, row, column, result_value, events)

    if src_meta:
        print(f"Why is {column} = {result_value}?")
        print()

        print("Source:")
        if src_meta["source_type"] == "http":
            print(f"{src_meta.get('method', 'GET')} {src_meta.get('url', '')}")
        else:
            print(src_meta.get("source_path", "Tracked object"))
        print()

        print("Format:")
        print(src_meta["source_format"])
        print()

        if "status_code" in src_meta and src_meta["status_code"] is not None:
            print("Status:")
            print(src_meta["status_code"])
            print()

        if "csv_row" in src_meta:
            print("Source row:")
            print(src_meta["csv_row"])
            print()

        elif "json_path" in src_meta:
            print("Path:")
            print(src_meta["json_path"])
            print()

        if not events:
            print("Original:")
            print(f"{column} = {result_value}")
            print()
            print("Final:")
            print(f"{column} = {result_value}")
            return

        print("Transformations:")
        print()
        for idx, event in enumerate(events, start=1):
            print(f"{idx}. {_format_event_summary(event)}")

        print()
        print("Final:")
        print(f"{column} = {result_value}")
        return

    print(f"Why is {column} = {result_value}?")
    print()

    if len(events) == 1:
        _explain_column(
            obj,
            row,
            column,
        )
    else:
        _explain_event_chain(
            obj,
            row,
            column,
            events,
        )


def explain_removed(obj=None, row=None):
    """Explain why a row was removed by a filter or dropna."""

    if row is None:
        print("Please provide a row.")
        return

    filter_event = _find_filter_for_row(
        row,
        obj,
    )

    if filter_event is None:
        print(f"No removal explanation found for row {row}.")
        return

    if filter_event["type"] == "dropna":
        print(f"Why was row {row} removed?")
        print()
        print(f"dropna(subset={filter_event['subset']})")
        print()
        print("Row removed because required data was missing.")
        return

    if filter_event["type"] == "combined_filter":
        print(f"Why was row {row} removed?")
        print()
        print(f"Combined filter ({filter_event['logic'].upper()}):")
        print()

        for condition in filter_event["conditions"]:
            print(f"{condition['column']} {condition['operator']} {condition['value']}")

        print()
        if filter_event["logic"] == "and":
            print("Row removed because the row did not satisfy all conditions.")

        elif filter_event["logic"] == "or":
            print("Row removed because the row did not satisfy any condition.")
        return

    column = filter_event["column"]
    operator = filter_event["operator"]
    threshold = filter_event["value"]
    row_value = filter_event["removed_values"][row]

    print(f"Why was row {row} removed?")
    print()

    fill_event = None

    if obj is not None:
        fill_event = _find_event_by_type(
            obj,
            column,
            "column_filled",
        )

    if fill_event is None:
        dataframe_id = filter_event.get("source_dataframe_id") or filter_event.get(
            "dataframe_id"
        )

        for event in reversed(history.get_all()):
            if (
                event.get("dataframe_id") == dataframe_id
                and event.get("column") == column
                and event["type"] == "column_filled"
            ):
                fill_event = event
                break

    if fill_event is not None and row in fill_event["missing_rows"]:
        fill_value = fill_event["value"]

        print(f"Original {column}:")
        print("NaN")
        print()

        print("Transformation:")
        print(f"fillna({fill_value})")
        print()

        print(f"NaN → {row_value}")
        print()

    print("Filter:")
    print(f"{column} {operator} {threshold}")
    print()

    print(f"{row_value} {operator} {threshold} → False")
    print()

    print("Row removed")
