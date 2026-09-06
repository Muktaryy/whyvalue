import pandas as pd

from .history import history
from .adapters import pandas as pandas_adapter


_watching = False


def watch():
    """Start WhyValue tracking."""
    global _watching

    if _watching:
        print("WhyValue is already watching.")
        return

    history.clear()
    pandas_adapter.enable()

    _watching = True

    print("WhyValue is watching your data.")


def stop():
    """Stop WhyValue tracking."""
    global _watching

    if not _watching:
        print("WhyValue is not currently watching.")
        return

    pandas_adapter.disable()

    _watching = False

    print("WhyValue stopped watching.")


def is_watching():
    """Return whether WhyValue is currently watching."""
    return _watching


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
        if event["type"] == "column_created":
            symbol = _get_symbol(event["operation"])

            print(f"{event['column']} = {event['left']} {symbol} {event['right']}")

        elif event["type"] == "column_filled":
            print(f"{event['column']}: missing values → {event['value']}")

        elif event["type"] == "filter":
            print(f"filter: {event['column']} {event['operator']} {event['value']}")


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
        result_value = obj.loc[row, column]
        fill_value = event["value"]

        if row in event["missing_rows"]:
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


def explain(obj, row, column=None):
    """Explain why a specific cell has its current value."""
    if isinstance(obj, pd.Series) and column is None:
        column = obj.name

    events = _find_events(
        obj,
        column,
    )

    if not events:
        print(f"No explanation found for '{column}'.")
        return

    if isinstance(obj, pd.Series):
        result_value = obj.loc[row]
    else:
        result_value = obj.loc[row, column]

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
