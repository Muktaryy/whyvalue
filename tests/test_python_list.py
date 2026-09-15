import pandas as pd
import pytest

import whyvalue as why
from whyvalue.adapters.python_list import TrackedList
from whyvalue.core import _find_list_events
from whyvalue.history import history


def test_track_list_basic_and_compatibility():
    with why.watch():
        items = why.track([10, 20])

        assert isinstance(items, list)
        assert isinstance(items, TrackedList)
        assert len(items) == 2
        assert items[0] == 10
        assert items[1] == 20
        assert list(items) == [10, 20]


def test_stable_object_identity():
    with why.watch():
        list1 = why.track([1, 2])
        list2 = why.track([3, 4])

        assert hasattr(list1, "_whyvalue_id")
        assert hasattr(list2, "_whyvalue_id")
        assert list1._whyvalue_id != list2._whyvalue_id


def test_list_operations_tracking():
    with why.watch():
        items = why.track([10, 20])

        items.append(30)
        assert items == [10, 20, 30]

        items.extend([40, 50])
        assert items == [10, 20, 30, 40, 50]

        items.insert(1, 15)
        assert items == [10, 15, 20, 30, 40, 50]

        items.remove(15)
        assert items == [10, 20, 30, 40, 50]

        popped = items.pop()
        assert popped == 50
        assert items == [10, 20, 30, 40]

        items[0] = 99
        assert items == [99, 20, 30, 40]

        del items[1]
        assert items == [99, 30, 40]

        items.clear()
        assert items == []

        events = _find_list_events(items)
        # created, append, extend, insert, remove, pop, setitem, delitem, clear = 9 events
        assert len(events) == 9


def test_chronological_multiple_operations():
    with why.watch():
        items = why.track([10, 20])
        items.append(30)
        items.append(40)

        events = _find_list_events(items)
        assert len(events) == 3
        assert events[0]["event_type"] == "list_created"
        assert events[1]["event_type"] == "list_append"
        assert events[1]["inputs"]["value"] == 30
        assert events[2]["event_type"] == "list_append"
        assert events[2]["inputs"]["value"] == 40


def test_historical_snapshot_mutation_isolation():
    with why.watch(snapshot=True):
        items = why.track([10, 20])
        items.append(30)
        items.append(40)

        events = _find_list_events(items)
        # Check event 1 (append 30) after_value is isolated snapshot [10, 20, 30]
        assert events[1].after_value == [10, 20, 30]
        assert events[2].after_value == [10, 20, 30, 40]

        # Mutate items further
        items.append(50)

        # Snapshot for append(30) remains [10, 20, 30]
        assert events[1].after_value == [10, 20, 30]


def test_explain_list_full(capsys):
    with why.watch():
        items = why.track([10, 20])
        items.append(30)

        why.explain(items)
        captured = capsys.readouterr().out

        assert "Why is this list [10, 20, 30]?" in captured
        assert "1. Created list [10, 20]" in captured
        assert "2. append(30)" in captured
        assert "Final:\n[10, 20, 30]" in captured


def test_explain_list_short(capsys):
    with why.watch():
        items = why.track([10, 20])
        items.append(30)

        res = why.explain(items, mode="short")
        captured = capsys.readouterr().out

        expected = "list: Created list [10, 20], append(30) → final: [10, 20, 30]"
        assert res == expected
        assert expected in captured


def test_explain_list_json():
    with why.watch(snapshot=True):
        items = why.track([10, 20])
        items.append(30)

        data = why.explain(items, mode="json")

        assert isinstance(data, dict)
        assert data["object_type"] == "list"
        assert data["object_id"] == items._whyvalue_id
        assert data["final_value"] == [10, 20, 30]
        assert len(data["steps"]) == 2

        assert data["steps"][0]["event_type"] == "list_created"
        assert data["steps"][1]["event_type"] == "list_append"
        assert data["steps"][1]["before"] == [10, 20]
        assert data["steps"][1]["after"] == [10, 20, 30]


def test_unsupported_track_type():
    with why.watch():
        for unsupported in (42, 3.14, "hello", (1, 2), {1, 2}):
            with pytest.raises(
                TypeError,
                match="WhyValue tracking does not support this object type yet.",
            ):
                why.track(unsupported)


def test_track_outside_watch_behavior():
    assert why.is_watching() is False
    with pytest.raises(
        RuntimeError,
        match=r"why\.track\(\) requires an active WhyValue watch session\.",
    ):
        why.track([10, 20])


def test_pandas_unaffected():
    with why.watch():
        df = pd.DataFrame({"a": [1.0, None, 3.0]})
        df["a"] = df["a"].fillna(0.0)

        items = why.track([1, 2])
        items.append(3)

        assert len(history.get_all()) == 3
        why.explain(df, 1, "a")
        why.explain(items)
