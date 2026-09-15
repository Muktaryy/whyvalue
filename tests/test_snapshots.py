import pandas as pd
import whyvalue as why
from whyvalue.core import is_snapshot_enabled
from whyvalue.history import history


def test_watch_default_snapshot_disabled():
    why.watch()
    assert why.is_watching() is True
    assert is_snapshot_enabled() is False

    df = pd.DataFrame({"price": [10.0, None, 30.0]})
    df["price"] = df["price"].fillna(0.0)

    events = [e for e in history.get_all() if e.get("type") == "column_filled"]
    assert len(events) == 1
    event = events[0]

    assert event.before_value is None
    assert event.after_value is None
    assert event.get("before_value") is None
    assert event.get("after_value") is None

    why.stop()
    assert why.is_watching() is False
    assert is_snapshot_enabled() is False


def test_watch_snapshot_enabled_captures_fillna_historical_values():
    why.watch(snapshot=True)
    assert why.is_watching() is True
    assert is_snapshot_enabled() is True

    df = pd.DataFrame({"price": [10.0, None, 30.0]})
    df["price"] = df["price"].fillna(0.0)

    events = [e for e in history.get_all() if e.get("type") == "column_filled"]
    assert len(events) == 1
    event = events[0]

    assert event.before_value is not None
    assert event.after_value is not None

    # Row 1 check
    assert pd.isna(event.before_value.iloc[1])
    assert event.after_value.iloc[1] == 0.0

    # Row 0 check
    assert event.before_value.iloc[0] == 10.0
    assert event.after_value.iloc[0] == 10.0

    why.stop()
    assert why.is_watching() is False
    assert is_snapshot_enabled() is False


def test_snapshot_mutation_isolation():
    why.watch(snapshot=True)

    df = pd.DataFrame({"price": [10.0, None, 30.0]})
    df["price"] = df["price"].fillna(0.0)

    events = [e for e in history.get_all() if e.get("type") == "column_filled"]
    assert len(events) == 1
    event = events[0]

    # Mutate DataFrame after fillna operation
    df["price"] = [999.0, 999.0, 999.0]
    df.loc[1, "price"] = 777.0

    # Verify stored historical snapshot is isolated and unchanged
    assert pd.isna(event.before_value.iloc[1])
    assert event.after_value.iloc[1] == 0.0
    assert event.before_value.iloc[0] == 10.0
    assert event.after_value.iloc[0] == 10.0

    why.stop()


def test_watch_stop_repeated_snapshot_toggle():
    why.watch()
    assert is_snapshot_enabled() is False
    why.stop()
    assert is_snapshot_enabled() is False

    why.watch(snapshot=True)
    assert is_snapshot_enabled() is True
    why.stop()
    assert is_snapshot_enabled() is False

    why.watch(snapshot=False)
    assert is_snapshot_enabled() is False
    why.stop()
