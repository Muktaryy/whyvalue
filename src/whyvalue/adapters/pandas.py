import copy
import uuid

import pandas as pd
from pandas.core.groupby.generic import DataFrameGroupBy, SeriesGroupBy

from ..history import history
from ..provenance import ProvenanceEvent
from .python_list import TrackedList
from .python_dict import TrackedDict


def to_dataframe(data):
    """Convert a WhyValue tracked container to a pandas DataFrame with cross-source provenance."""
    from ..core import is_watching

    if not is_watching():
        raise RuntimeError(
            "why.to_dataframe() requires an active WhyValue watch session."
        )

    if not isinstance(data, (TrackedList, TrackedDict)) and not hasattr(
        data, "_whyvalue_id"
    ):
        raise TypeError(
            f"why.to_dataframe() expects a tracked object (TrackedList or TrackedDict), got {type(data).__name__}."
        )

    df = pd.DataFrame(list(data) if isinstance(data, (list, TrackedList)) else data)

    # Ensure fresh DataFrame identity
    df_id = uuid.uuid4().hex
    df.attrs["_whyvalue_id"] = df_id

    source_id = getattr(data, "_whyvalue_id", None)
    source_type = (
        "list"
        if isinstance(data, (list, TrackedList))
        else ("dict" if isinstance(data, (dict, TrackedDict)) else "object")
    )

    source_meta = getattr(data, "_whyvalue_source", None)
    if not source_meta:
        source_meta = {
            "source_type": source_type,
            "source_format": "Python object",
        }

    df.attrs["_whyvalue_source"] = copy.deepcopy(source_meta)
    if source_id:
        df.attrs["_whyvalue_source_id"] = source_id

    history.add(
        ProvenanceEvent(
            event_type="to_dataframe",
            object_id=df_id,
            dataframe_id=df_id,
            source_id=source_id,
            inputs={
                "source_id": source_id,
                "source_object_type": source_type,
                "columns": list(df.columns),
                "row_count": len(df),
            },
            metadata={
                "operation": "to_dataframe",
                "source_id": source_id,
                "dataframe_id": df_id,
                "source_object_type": source_type,
                "columns": list(df.columns),
                "row_count": len(df),
                "source_metadata": copy.deepcopy(source_meta),
            },
        )
    )

    return df


_original_add = None
_original_radd = None
_original_mul = None
_original_rmul = None
_original_sub = None
_original_rsub = None
_original_truediv = None
_original_rtruediv = None

_original_gt = None
_original_ge = None
_original_lt = None
_original_le = None
_original_eq = None
_original_ne = None
_original_and = None
_original_or = None

_original_fillna = None
_original_astype = None
_original_round = None
_original_map = None
_original_apply = None
_original_dropna = None
_original_rename = None
_original_copy = None
_original_merge = None
_original_groupby = None
_original_groupby_getitem = None
_original_series_groupby_sum = None
_original_series_groupby_mean = None
_original_series_groupby_count = None
_original_series_groupby_min = None
_original_series_groupby_max = None
_original_setitem = None
_original_getitem = None

_enabled = False


def _get_dataframe_id(df):
    """Get or create a stable WhyValue ID for a DataFrame."""
    dataframe_id = df.attrs.get("_whyvalue_id")

    if dataframe_id is None:
        dataframe_id = uuid.uuid4().hex
        df.attrs["_whyvalue_id"] = dataframe_id

    return dataframe_id


def _add_filter_info(result, series, operator, value):
    """Attach filter information to a boolean Series."""
    result.attrs["_whyvalue_filter"] = {
        "column": series.name,
        "operator": operator,
        "value": value,
    }

    return result


def enable(snapshot=False):
    global _original_add
    global _original_radd
    global _original_mul
    global _original_rmul
    global _original_sub
    global _original_rsub
    global _original_truediv
    global _original_rtruediv

    global _original_gt
    global _original_ge
    global _original_lt
    global _original_le
    global _original_eq
    global _original_ne
    global _original_and
    global _original_or

    global _original_fillna
    global _original_astype
    global _original_round
    global _original_map
    global _original_apply
    global _original_dropna
    global _original_rename
    global _original_copy
    global _original_merge
    global _original_groupby
    global _original_groupby_getitem
    global _original_series_groupby_sum
    global _original_series_groupby_mean
    global _original_series_groupby_count
    global _original_series_groupby_min
    global _original_series_groupby_max
    global _original_setitem
    global _original_getitem
    global _enabled
    global _snapshot_enabled

    _snapshot_enabled = bool(snapshot)

    if _enabled:
        return

    _original_add = pd.Series.__add__
    _original_radd = pd.Series.__radd__
    _original_mul = pd.Series.__mul__
    _original_rmul = pd.Series.__rmul__
    _original_sub = pd.Series.__sub__
    _original_rsub = pd.Series.__rsub__
    _original_truediv = pd.Series.__truediv__
    _original_rtruediv = pd.Series.__rtruediv__

    _original_gt = pd.Series.__gt__
    _original_ge = pd.Series.__ge__
    _original_lt = pd.Series.__lt__
    _original_le = pd.Series.__le__
    _original_eq = pd.Series.__eq__
    _original_ne = pd.Series.__ne__
    _original_and = pd.Series.__and__
    _original_or = pd.Series.__or__

    _original_fillna = pd.Series.fillna
    _original_astype = pd.Series.astype
    _original_round = pd.Series.round
    _original_map = pd.Series.map
    _original_apply = pd.Series.apply
    _original_dropna = pd.DataFrame.dropna
    _original_rename = pd.DataFrame.rename
    _original_copy = pd.DataFrame.copy
    _original_merge = pd.DataFrame.merge
    _original_groupby = pd.DataFrame.groupby
    _original_groupby_getitem = DataFrameGroupBy.__getitem__
    _original_series_groupby_sum = SeriesGroupBy.sum
    _original_series_groupby_mean = SeriesGroupBy.mean
    _original_series_groupby_count = SeriesGroupBy.count
    _original_series_groupby_min = SeriesGroupBy.min
    _original_series_groupby_max = SeriesGroupBy.max
    _original_setitem = pd.DataFrame.__setitem__
    _original_getitem = pd.DataFrame.__getitem__

    def whyvalue_add(left, right):
        result = _original_add(left, right)

        left_df_id = left.attrs.get("_whyvalue_dataframe_id") or left.attrs.get(
            "_whyvalue_id"
        )

        if isinstance(right, pd.Series):
            right_df_id = right.attrs.get("_whyvalue_dataframe_id") or right.attrs.get(
                "_whyvalue_id"
            )
            info = {
                "operation": "add",
                "left": left.name,
                "right": right.name,
                "right_type": "column",
            }
            if left_df_id:
                info["left_dataframe_id"] = left_df_id
            if right_df_id:
                info["right_dataframe_id"] = right_df_id
            result.attrs["_whyvalue"] = info
        else:
            info = {
                "operation": "add",
                "left": left.name,
                "right": right,
                "right_type": "scalar",
            }
            if left_df_id:
                info["left_dataframe_id"] = left_df_id
            result.attrs["_whyvalue"] = info

        return result

    def whyvalue_radd(series, other):
        result = _original_radd(series, other)

        series_df_id = series.attrs.get("_whyvalue_dataframe_id") or series.attrs.get(
            "_whyvalue_id"
        )

        info = {
            "operation": "add",
            "left": other,
            "left_type": "scalar",
            "right": series.name,
            "right_type": "column",
        }
        if series_df_id:
            info["right_dataframe_id"] = series_df_id

        result.attrs["_whyvalue"] = info

        return result

    def whyvalue_mul(left, right):
        result = _original_mul(left, right)

        left_df_id = left.attrs.get("_whyvalue_dataframe_id") or left.attrs.get(
            "_whyvalue_id"
        )

        if isinstance(right, pd.Series):
            right_df_id = right.attrs.get("_whyvalue_dataframe_id") or right.attrs.get(
                "_whyvalue_id"
            )
            info = {
                "operation": "multiply",
                "left": left.name,
                "right": right.name,
                "right_type": "column",
            }
            if left_df_id:
                info["left_dataframe_id"] = left_df_id
            if right_df_id:
                info["right_dataframe_id"] = right_df_id
            result.attrs["_whyvalue"] = info
        else:
            info = {
                "operation": "multiply",
                "left": left.name,
                "right": right,
                "right_type": "scalar",
            }
            if left_df_id:
                info["left_dataframe_id"] = left_df_id
            result.attrs["_whyvalue"] = info

        return result

    def whyvalue_rmul(series, other):
        result = _original_rmul(series, other)

        series_df_id = series.attrs.get("_whyvalue_dataframe_id") or series.attrs.get(
            "_whyvalue_id"
        )

        info = {
            "operation": "multiply",
            "left": other,
            "left_type": "scalar",
            "right": series.name,
            "right_type": "column",
        }
        if series_df_id:
            info["right_dataframe_id"] = series_df_id

        result.attrs["_whyvalue"] = info

        return result

    def whyvalue_sub(left, right):
        result = _original_sub(left, right)

        left_df_id = left.attrs.get("_whyvalue_dataframe_id") or left.attrs.get(
            "_whyvalue_id"
        )

        if isinstance(right, pd.Series):
            right_df_id = right.attrs.get("_whyvalue_dataframe_id") or right.attrs.get(
                "_whyvalue_id"
            )
            info = {
                "operation": "subtract",
                "left": left.name,
                "right": right.name,
                "right_type": "column",
            }
            if left_df_id:
                info["left_dataframe_id"] = left_df_id
            if right_df_id:
                info["right_dataframe_id"] = right_df_id
            result.attrs["_whyvalue"] = info
        else:
            info = {
                "operation": "subtract",
                "left": left.name,
                "right": right,
                "right_type": "scalar",
            }
            if left_df_id:
                info["left_dataframe_id"] = left_df_id
            result.attrs["_whyvalue"] = info

        return result

    def whyvalue_rsub(series, other):
        result = _original_rsub(series, other)

        series_df_id = series.attrs.get("_whyvalue_dataframe_id") or series.attrs.get(
            "_whyvalue_id"
        )

        info = {
            "operation": "subtract",
            "left": other,
            "left_type": "scalar",
            "right": series.name,
            "right_type": "column",
        }
        if series_df_id:
            info["right_dataframe_id"] = series_df_id

        result.attrs["_whyvalue"] = info

        return result

    def whyvalue_truediv(left, right):
        result = _original_truediv(left, right)

        left_df_id = left.attrs.get("_whyvalue_dataframe_id") or left.attrs.get(
            "_whyvalue_id"
        )

        if isinstance(right, pd.Series):
            right_df_id = right.attrs.get("_whyvalue_dataframe_id") or right.attrs.get(
                "_whyvalue_id"
            )
            info = {
                "operation": "divide",
                "left": left.name,
                "right": right.name,
                "right_type": "column",
            }
            if left_df_id:
                info["left_dataframe_id"] = left_df_id
            if right_df_id:
                info["right_dataframe_id"] = right_df_id
            result.attrs["_whyvalue"] = info
        else:
            info = {
                "operation": "divide",
                "left": left.name,
                "right": right,
                "right_type": "scalar",
            }
            if left_df_id:
                info["left_dataframe_id"] = left_df_id
            result.attrs["_whyvalue"] = info

        return result

    def whyvalue_rtruediv(series, other):
        result = _original_rtruediv(series, other)

        series_df_id = series.attrs.get("_whyvalue_dataframe_id") or series.attrs.get(
            "_whyvalue_id"
        )

        info = {
            "operation": "divide",
            "left": other,
            "left_type": "scalar",
            "right": series.name,
            "right_type": "column",
        }
        if series_df_id:
            info["right_dataframe_id"] = series_df_id

        result.attrs["_whyvalue"] = info

        return result

    def whyvalue_gt(series, other):
        result = _original_gt(series, other)

        return _add_filter_info(
            result,
            series,
            ">",
            other,
        )

    def whyvalue_ge(series, other):
        result = _original_ge(series, other)

        return _add_filter_info(
            result,
            series,
            ">=",
            other,
        )

    def whyvalue_lt(series, other):
        result = _original_lt(series, other)

        return _add_filter_info(
            result,
            series,
            "<",
            other,
        )

    def whyvalue_le(series, other):
        result = _original_le(series, other)

        return _add_filter_info(
            result,
            series,
            "<=",
            other,
        )

    def whyvalue_eq(series, other):
        result = _original_eq(series, other)

        return _add_filter_info(
            result,
            series,
            "==",
            other,
        )

    def whyvalue_ne(series, other):
        result = _original_ne(series, other)

        return _add_filter_info(
            result,
            series,
            "!=",
            other,
        )

    def whyvalue_and(left, right):
        result = _original_and(left, right)

        left_info = left.attrs.get("_whyvalue_filter")
        right_info = (
            right.attrs.get("_whyvalue_filter")
            if isinstance(right, pd.Series)
            else None
        )

        if left_info and right_info:
            result.attrs["_whyvalue_filter"] = {
                "type": "combined_filter",
                "logic": "and",
                "conditions": [left_info, right_info],
            }

        else:
            result.attrs.pop("_whyvalue_filter", None)

        return result

    def whyvalue_or(left, right):
        result = _original_or(left, right)

        left_info = left.attrs.get("_whyvalue_filter")
        right_info = (
            right.attrs.get("_whyvalue_filter")
            if isinstance(right, pd.Series)
            else None
        )

        if left_info and right_info:
            result.attrs["_whyvalue_filter"] = {
                "type": "combined_filter",
                "logic": "or",
                "conditions": [left_info, right_info],
            }

        else:
            result.attrs.pop("_whyvalue_filter", None)

        return result

    def whyvalue_fillna(series, value=None, *args, **kwargs):
        missing_rows = series[series.isna()].index.tolist()

        before_snapshot = series.copy(deep=True) if _snapshot_enabled else None

        result = _original_fillna(series, value=value, *args, **kwargs)

        after_snapshot = result.copy(deep=True) if _snapshot_enabled else None

        result.attrs["_whyvalue"] = {
            "operation": "fillna",
            "source": series.name,
            "value": value,
            "missing_rows": missing_rows,
            "before_value": before_snapshot,
            "after_value": after_snapshot,
        }

        return result

    def whyvalue_astype(series, dtype, *args, **kwargs):
        result = _original_astype(series, dtype, *args, **kwargs)

        result.attrs["_whyvalue"] = {
            "operation": "astype",
            "source": series.name,
            "dtype": str(dtype),
        }

        return result

    def whyvalue_round(series, decimals=0, *args, **kwargs):
        result = _original_round(series, decimals, *args, **kwargs)

        result.attrs["_whyvalue"] = {
            "operation": "round",
            "source": series.name,
            "decimals": decimals,
        }

        return result

    def whyvalue_map(series, arg, *args, **kwargs):
        result = _original_map(series, arg, *args, **kwargs)

        if isinstance(arg, dict):
            result.attrs["_whyvalue"] = {
                "operation": "map",
                "source": series.name,
                "mapping": dict(arg),
            }

        else:
            result.attrs.pop("_whyvalue", None)

        return result

    def whyvalue_apply(series, func, *args, **kwargs):
        result = _original_apply(series, func, *args, **kwargs)

        func_name = getattr(func, "__name__", None)
        if not func_name:
            func_name = type(func).__name__

        if isinstance(result, pd.Series):
            result.attrs["_whyvalue"] = {
                "operation": "apply",
                "source": series.name,
                "function": func_name,
            }

        return result

    def whyvalue_dropna(df, *args, **kwargs):
        source_id = _get_dataframe_id(df)
        before = df.copy(deep=False)

        result = _original_dropna(df, *args, **kwargs)
        is_inplace = result is None or kwargs.get("inplace", False)

        if is_inplace:
            result_id = source_id
            remaining = df
        else:
            result_id = uuid.uuid4().hex
            remaining = result
            remaining.attrs["_whyvalue_id"] = result_id

        if len(remaining) < len(before):
            # Use positions to retain original labels, even with ignore_index
            # or duplicate row labels. Let pandas determine which rows survive.
            original_index = before.index
            before.index = pd.RangeIndex(len(before))
            tracking_kwargs = dict(kwargs, inplace=False, ignore_index=False)
            kept = _original_dropna(before, *args, **tracking_kwargs)
            removed_rows = original_index[~before.index.isin(kept.index)].tolist()

            subset = kwargs.get("subset")
            if subset is None:
                subset = before.columns.tolist()
            elif pd.api.types.is_list_like(subset):
                subset = list(subset)
            else:
                subset = [subset]

            history.add(
                {
                    "type": "dropna",
                    "dataframe_id": result_id,
                    "source_dataframe_id": source_id,
                    "subset": subset,
                    "removed_rows": removed_rows,
                }
            )

        return result

    def whyvalue_rename(df, *args, **kwargs):
        source_id = _get_dataframe_id(df)
        original_columns = df.columns.copy()

        result = _original_rename(df, *args, **kwargs)
        is_inplace = result is None or kwargs.get("inplace", False)

        if is_inplace:
            result_id = source_id
            renamed = df
        else:
            result_id = uuid.uuid4().hex
            renamed = result
            renamed.attrs["_whyvalue_id"] = result_id

        columns = kwargs.get("columns")
        if (
            columns is not None
            and hasattr(columns, "items")
            and not original_columns.equals(renamed.columns)
        ):
            history.add(
                {
                    "type": "rename",
                    "dataframe_id": result_id,
                    "source_dataframe_id": source_id,
                    "columns": dict(columns.items()),
                }
            )

        return result

    def whyvalue_copy(df, *args, **kwargs):
        result = _original_copy(df, *args, **kwargs)

        if isinstance(result, pd.DataFrame):
            result.attrs["_whyvalue_id"] = uuid.uuid4().hex

        return result

    def whyvalue_merge(self, right, *args, **kwargs):
        left_dataframe_id = _get_dataframe_id(self)
        right_dataframe_id = _get_dataframe_id(right)

        result = _original_merge(self, right, *args, **kwargs)

        new_dataframe_id = uuid.uuid4().hex
        result.attrs["_whyvalue_id"] = new_dataframe_id

        how = kwargs.get("how")
        if how is None:
            if len(args) >= 1:
                how = args[0]
            else:
                how = "inner"

        on = kwargs.get("on")
        if on is None and len(args) >= 2:
            on = args[1]

        history.add(
            {
                "type": "merge",
                "dataframe_id": new_dataframe_id,
                "left_dataframe_id": left_dataframe_id,
                "right_dataframe_id": right_dataframe_id,
                "on": on,
                "how": how,
            }
        )

        return result

    def whyvalue_groupby(df, by, *args, **kwargs):
        dataframe_id = _get_dataframe_id(df)
        gb = _original_groupby(df, by, *args, **kwargs)

        gb._whyvalue_info = {
            "dataframe_id": dataframe_id,
            "group_by": by,
        }

        return gb

    def whyvalue_groupby_getitem(gb, key):
        sgb = _original_groupby_getitem(gb, key)

        if hasattr(gb, "_whyvalue_info"):
            sgb._whyvalue_info = dict(gb._whyvalue_info)
            sgb._whyvalue_info["source"] = key

        return sgb

    def whyvalue_series_groupby_sum(sgb, *args, **kwargs):
        result = _original_series_groupby_sum(sgb, *args, **kwargs)

        if hasattr(sgb, "_whyvalue_info"):
            info = sgb._whyvalue_info
            result_id = uuid.uuid4().hex
            result.attrs["_whyvalue_id"] = result_id

            history.add(
                {
                    "type": "groupby",
                    "dataframe_id": result_id,
                    "source_dataframe_id": info["dataframe_id"],
                    "group_by": info["group_by"],
                    "source": info["source"],
                    "aggregation": "sum",
                }
            )

        return result

    def whyvalue_series_groupby_mean(sgb, *args, **kwargs):
        result = _original_series_groupby_mean(sgb, *args, **kwargs)

        if hasattr(sgb, "_whyvalue_info"):
            info = sgb._whyvalue_info
            result_id = uuid.uuid4().hex
            result.attrs["_whyvalue_id"] = result_id

            history.add(
                {
                    "type": "groupby",
                    "dataframe_id": result_id,
                    "source_dataframe_id": info["dataframe_id"],
                    "group_by": info["group_by"],
                    "source": info["source"],
                    "aggregation": "mean",
                }
            )

        return result

    def whyvalue_series_groupby_count(sgb, *args, **kwargs):
        result = _original_series_groupby_count(sgb, *args, **kwargs)

        if hasattr(sgb, "_whyvalue_info"):
            info = sgb._whyvalue_info
            result_id = uuid.uuid4().hex
            result.attrs["_whyvalue_id"] = result_id

            history.add(
                {
                    "type": "groupby",
                    "dataframe_id": result_id,
                    "source_dataframe_id": info["dataframe_id"],
                    "group_by": info["group_by"],
                    "source": info["source"],
                    "aggregation": "count",
                }
            )

        return result

    def whyvalue_series_groupby_min(sgb, *args, **kwargs):
        result = _original_series_groupby_min(sgb, *args, **kwargs)

        if hasattr(sgb, "_whyvalue_info"):
            info = sgb._whyvalue_info
            result_id = uuid.uuid4().hex
            result.attrs["_whyvalue_id"] = result_id

            history.add(
                {
                    "type": "groupby",
                    "dataframe_id": result_id,
                    "source_dataframe_id": info["dataframe_id"],
                    "group_by": info["group_by"],
                    "source": info["source"],
                    "aggregation": "min",
                }
            )

        return result

    def whyvalue_series_groupby_max(sgb, *args, **kwargs):
        result = _original_series_groupby_max(sgb, *args, **kwargs)

        if hasattr(sgb, "_whyvalue_info"):
            info = sgb._whyvalue_info
            result_id = uuid.uuid4().hex
            result.attrs["_whyvalue_id"] = result_id

            history.add(
                {
                    "type": "groupby",
                    "dataframe_id": result_id,
                    "source_dataframe_id": info["dataframe_id"],
                    "group_by": info["group_by"],
                    "source": info["source"],
                    "aggregation": "max",
                }
            )

        return result

    def whyvalue_setitem(df, key, value):
        dataframe_id = _get_dataframe_id(df)

        _original_setitem(df, key, value)

        if isinstance(value, pd.Series):
            info = value.attrs.get("_whyvalue")

            if info:
                if info["operation"] == "fillna":
                    event_data = {
                        "type": "column_filled",
                        "dataframe_id": dataframe_id,
                        "column": key,
                        "source": info["source"],
                        "operation": "fillna",
                        "value": info["value"],
                        "missing_rows": info["missing_rows"],
                    }
                    if info.get("before_value") is not None:
                        event_data["before_value"] = info["before_value"]
                    if info.get("after_value") is not None:
                        event_data["after_value"] = info["after_value"]

                    history.add(event_data)

                elif info["operation"] == "astype":
                    history.add(
                        {
                            "type": "astype",
                            "dataframe_id": dataframe_id,
                            "column": key,
                            "source": info["source"],
                            "dtype": info["dtype"],
                        }
                    )

                elif info["operation"] == "round":
                    history.add(
                        {
                            "type": "round",
                            "dataframe_id": dataframe_id,
                            "column": key,
                            "source": info["source"],
                            "decimals": info["decimals"],
                        }
                    )

                elif info["operation"] == "map":
                    history.add(
                        {
                            "type": "map",
                            "dataframe_id": dataframe_id,
                            "column": key,
                            "source": info["source"],
                            "mapping": info["mapping"],
                        }
                    )

                elif info["operation"] == "apply":
                    history.add(
                        {
                            "type": "apply",
                            "dataframe_id": dataframe_id,
                            "column": key,
                            "source": info["source"],
                            "function": info["function"],
                        }
                    )

                else:
                    event = {
                        "type": "column_created",
                        "dataframe_id": dataframe_id,
                        "column": key,
                        "operation": info["operation"],
                        "left": info["left"],
                        "right": info["right"],
                    }

                    if "left_type" in info:
                        event["left_type"] = info["left_type"]

                    if "right_type" in info:
                        event["right_type"] = info["right_type"]

                    if "left_dataframe_id" in info:
                        event["left_dataframe_id"] = info["left_dataframe_id"]

                    if "right_dataframe_id" in info:
                        event["right_dataframe_id"] = info["right_dataframe_id"]

                    history.add(event)
            else:
                source_dataframe_id = value.attrs.get(
                    "_whyvalue_dataframe_id"
                ) or value.attrs.get("_whyvalue_id")
                if source_dataframe_id and source_dataframe_id != dataframe_id:
                    source_name = value.name if value.name is not None else key
                    history.add(
                        {
                            "type": "column_created",
                            "dataframe_id": dataframe_id,
                            "column": key,
                            "operation": "copy",
                            "source": source_name,
                            "source_dataframe_id": source_dataframe_id,
                        }
                    )

    def whyvalue_getitem(df, key):
        dataframe_id = _get_dataframe_id(df)

        result = _original_getitem(df, key)

        if isinstance(result, pd.Series):
            result.attrs["_whyvalue_dataframe_id"] = dataframe_id

        if isinstance(key, pd.Series):
            info = key.attrs.get("_whyvalue_filter")

            if info and info.get("type") == "combined_filter":
                result_id = uuid.uuid4().hex
                if isinstance(result, pd.DataFrame):
                    result.attrs["_whyvalue_id"] = result_id

                mask = key.reindex(df.index).fillna(False)
                history.add(
                    {
                        "type": "combined_filter",
                        "dataframe_id": result_id,
                        "source_dataframe_id": dataframe_id,
                        "logic": info["logic"],
                        "conditions": info["conditions"],
                        "removed_rows": df.index[~mask].tolist(),
                    }
                )

                return result

            if info:
                result_id = uuid.uuid4().hex
                if isinstance(result, pd.DataFrame):
                    result.attrs["_whyvalue_id"] = result_id

                removed_rows = df.index[~key].tolist()

                removed_values = {
                    row: df.loc[row, info["column"]] for row in removed_rows
                }

                history.add(
                    {
                        "type": "filter",
                        "dataframe_id": result_id,
                        "source_dataframe_id": dataframe_id,
                        "column": info["column"],
                        "operator": info["operator"],
                        "value": info["value"],
                        "removed_rows": removed_rows,
                        "removed_values": removed_values,
                    }
                )

        return result

    pd.Series.__add__ = whyvalue_add
    pd.Series.__radd__ = whyvalue_radd
    pd.Series.__mul__ = whyvalue_mul
    pd.Series.__rmul__ = whyvalue_rmul
    pd.Series.__sub__ = whyvalue_sub
    pd.Series.__rsub__ = whyvalue_rsub
    pd.Series.__truediv__ = whyvalue_truediv
    pd.Series.__rtruediv__ = whyvalue_rtruediv

    pd.Series.__gt__ = whyvalue_gt
    pd.Series.__ge__ = whyvalue_ge
    pd.Series.__lt__ = whyvalue_lt
    pd.Series.__le__ = whyvalue_le
    pd.Series.__eq__ = whyvalue_eq
    pd.Series.__ne__ = whyvalue_ne
    pd.Series.__and__ = whyvalue_and
    pd.Series.__or__ = whyvalue_or

    pd.Series.fillna = whyvalue_fillna
    pd.Series.astype = whyvalue_astype
    pd.Series.round = whyvalue_round
    pd.Series.map = whyvalue_map
    pd.Series.apply = whyvalue_apply
    pd.DataFrame.dropna = whyvalue_dropna
    pd.DataFrame.rename = whyvalue_rename
    pd.DataFrame.copy = whyvalue_copy
    pd.DataFrame.merge = whyvalue_merge
    pd.DataFrame.groupby = whyvalue_groupby
    DataFrameGroupBy.__getitem__ = whyvalue_groupby_getitem
    SeriesGroupBy.sum = whyvalue_series_groupby_sum
    SeriesGroupBy.mean = whyvalue_series_groupby_mean
    SeriesGroupBy.count = whyvalue_series_groupby_count
    SeriesGroupBy.min = whyvalue_series_groupby_min
    SeriesGroupBy.max = whyvalue_series_groupby_max
    pd.DataFrame.__setitem__ = whyvalue_setitem
    pd.DataFrame.__getitem__ = whyvalue_getitem

    _enabled = True


def disable():
    global _enabled

    if not _enabled:
        return

    pd.Series.__add__ = _original_add
    pd.Series.__radd__ = _original_radd
    pd.Series.__mul__ = _original_mul
    pd.Series.__rmul__ = _original_rmul
    pd.Series.__sub__ = _original_sub
    pd.Series.__rsub__ = _original_rsub
    pd.Series.__truediv__ = _original_truediv
    pd.Series.__rtruediv__ = _original_rtruediv

    pd.Series.__gt__ = _original_gt
    pd.Series.__ge__ = _original_ge
    pd.Series.__lt__ = _original_lt
    pd.Series.__le__ = _original_le
    pd.Series.__eq__ = _original_eq
    pd.Series.__ne__ = _original_ne
    pd.Series.__and__ = _original_and
    pd.Series.__or__ = _original_or

    pd.Series.fillna = _original_fillna
    pd.Series.astype = _original_astype
    pd.Series.round = _original_round
    pd.Series.map = _original_map
    pd.Series.apply = _original_apply
    pd.DataFrame.dropna = _original_dropna
    pd.DataFrame.rename = _original_rename
    pd.DataFrame.copy = _original_copy
    pd.DataFrame.merge = _original_merge
    pd.DataFrame.groupby = _original_groupby
    DataFrameGroupBy.__getitem__ = _original_groupby_getitem
    SeriesGroupBy.sum = _original_series_groupby_sum
    SeriesGroupBy.mean = _original_series_groupby_mean
    SeriesGroupBy.count = _original_series_groupby_count
    SeriesGroupBy.min = _original_series_groupby_min
    SeriesGroupBy.max = _original_series_groupby_max
    pd.DataFrame.__setitem__ = _original_setitem
    pd.DataFrame.__getitem__ = _original_getitem

    _enabled = False
