import pandas as pd
import pytest

import whyvalue as why
from whyvalue.core import WatchSession, is_snapshot_enabled
from whyvalue.history import history


def test_manual_watch_and_stop():
    """Verify existing manual why.watch() and why.stop() continue working."""
    why.watch()
    try:
        assert why.is_watching() is True
        df = pd.DataFrame({"a": [1.0, None, 3.0]})
        df["a"] = df["a"].fillna(0.0)

        events = history.get_all()
        assert len(events) == 1
        assert events[0]["type"] == "column_filled"
    finally:
        why.stop()

    assert why.is_watching() is False


def test_context_manager_basic():
    """Verify with why.watch(): activates tracking and stops automatically."""
    assert why.is_watching() is False

    with why.watch() as session:
        assert why.is_watching() is True
        assert isinstance(session, WatchSession)
        assert session.snapshot is False

        df = pd.DataFrame({"val": [None, 2.0]})
        df["val"] = df["val"].fillna(1.0)

        events = history.get_all()
        assert len(events) == 1

    assert why.is_watching() is False


def test_context_manager_snapshot():
    """Verify with why.watch(snapshot=True): enables snapshot capture and resets afterward."""
    assert why.is_watching() is False
    assert is_snapshot_enabled() is False

    with why.watch(snapshot=True) as session:
        assert why.is_watching() is True
        assert is_snapshot_enabled() is True
        assert session.snapshot is True

        df = pd.DataFrame({"price": [10.0, None, 30.0]})
        df["price"] = df["price"].fillna(0.0)

        events = history.get_all()
        assert len(events) == 1
        assert events[0].before_value is not None
        assert events[0].after_value is not None

    assert why.is_watching() is False
    assert is_snapshot_enabled() is False


def test_context_manager_automatic_stop_normal_exit():
    """Verify context manager automatically stops tracking on normal exit."""
    assert why.is_watching() is False

    with why.watch():
        assert why.is_watching() is True

    assert why.is_watching() is False


def test_context_manager_automatic_stop_on_exception():
    """Verify context manager automatically stops tracking even if an exception occurs inside."""
    assert why.is_watching() is False

    with pytest.raises(ValueError, match="Inner exception"):
        with why.watch():
            assert why.is_watching() is True
            raise ValueError("Inner exception")

    assert why.is_watching() is False


def test_context_manager_exception_propagation():
    """Verify exception inside with why.watch(): propagates unchanged."""

    class CustomTestError(Exception):
        pass

    with pytest.raises(CustomTestError):
        with why.watch():
            raise CustomTestError("custom error message")

    assert why.is_watching() is False


def test_repeated_context_manager_sessions():
    """Verify repeated context manager usage starts clean sessions each time."""

    with why.watch():
        df1 = pd.DataFrame({"a": [None, 1.0]})
        df1["a"] = df1["a"].fillna(0.0)
        assert len(history.get_all()) == 1

    assert why.is_watching() is False

    with why.watch():
        df2 = pd.DataFrame({"b": [None, 2.0]})
        df2["b"] = df2["b"].fillna(5.0)
        events = history.get_all()
        assert len(events) == 1
        assert events[0]["column"] == "b"

    assert why.is_watching() is False


def test_safe_nested_behavior():
    """Verify nested watch() calls are safe and do not raise RuntimeError."""

    with why.watch():
        assert why.is_watching() is True
        with why.watch():
            assert why.is_watching() is True

        # Outer tracking remains active inside outer block
        assert why.is_watching() is True

    # After outer block exits, watching is safely stopped
    assert why.is_watching() is False


def test_pandas_methods_restored_afterward():
    """Verify pandas methods are restored back to original functions after context exit."""

    with why.watch():
        assert pd.Series.fillna.__name__ == "whyvalue_fillna"

    # After exit, fillna is restored to pandas native implementation
    assert pd.Series.fillna.__name__ != "whyvalue_fillna"
