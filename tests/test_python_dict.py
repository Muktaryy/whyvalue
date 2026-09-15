import pandas as pd
import pytest

import whyvalue as why
from whyvalue.adapters.python_dict import TrackedDict
from whyvalue.core import _find_dict_events
from whyvalue.history import history


def test_track_dict_basic_and_isinstance():
    with why.watch():
        user = why.track({"name": "Ali", "age": 20})

        assert isinstance(user, dict)
        assert isinstance(user, TrackedDict)
        assert len(user) == 2
        assert user["name"] == "Ali"
        assert user["age"] == 20
        assert dict(user) == {"name": "Ali", "age": 20}


def test_stable_object_identity_and_creation_event():
    with why.watch():
        dict1 = why.track({"a": 1})
        dict2 = why.track({"b": 2})

        assert hasattr(dict1, "_whyvalue_id")
        assert hasattr(dict2, "_whyvalue_id")
        assert dict1._whyvalue_id != dict2._whyvalue_id

        events1 = _find_dict_events(dict1)
        assert len(events1) == 1
        assert events1[0]["event_type"] == "dict_created"
        assert events1[0]["object_id"] == dict1._whyvalue_id


def test_dict_setitem_and_overwrite():
    with why.watch():
        user = why.track({"age": 20})
        user["age"] = 21
        user["city"] = "Paris"

        assert user["age"] == 21
        assert user["city"] == "Paris"

        events = _find_dict_events(user)
        # created, setitem(age=21), setitem(city=Paris) = 3 events
        assert len(events) == 3
        assert events[1]["event_type"] == "dict_setitem"
        assert events[1]["inputs"]["key"] == "age"
        assert events[1]["inputs"]["value"] == 21


def test_dict_delete_item():
    with why.watch():
        user = why.track({"name": "Ali", "age": 20})
        del user["age"]

        assert "age" not in user
        events = _find_dict_events(user)
        assert len(events) == 2
        assert events[1]["event_type"] == "dict_delitem"
        assert events[1]["inputs"]["key"] == "age"


def test_dict_update():
    with why.watch():
        user = why.track({"name": "Ali"})
        user.update({"age": 25, "role": "admin"})

        assert user["age"] == 25
        assert user["role"] == "admin"

        events = _find_dict_events(user)
        assert len(events) == 2
        assert events[1]["event_type"] == "dict_update"
        assert events[1]["inputs"]["update_dict"] == {"age": 25, "role": "admin"}


def test_dict_pop():
    with why.watch():
        user = why.track({"name": "Ali", "age": 20})
        popped = user.pop("age")

        assert popped == 20
        assert "age" not in user

        events = _find_dict_events(user)
        assert len(events) == 2
        assert events[1]["event_type"] == "dict_pop"

        # Pop missing key with default
        val = user.pop("missing", "default_val")
        assert val == "default_val"

        # Pop missing key without default raises KeyError
        with pytest.raises(KeyError):
            user.pop("nonexistent")


def test_dict_popitem():
    with why.watch():
        user = why.track({"a": 1})
        k, v = user.popitem()

        assert k == "a"
        assert v == 1
        assert len(user) == 0

        # Empty popitem raises KeyError
        with pytest.raises(KeyError):
            user.popitem()


def test_dict_setdefault_missing_and_existing_key():
    with why.watch():
        user = why.track({"name": "Ali"})

        # Missing key -> inserts default
        v1 = user.setdefault("role", "guest")
        assert v1 == "guest"
        assert user["role"] == "guest"

        # Existing key -> returns current value without inserting/changing
        v2 = user.setdefault("role", "admin")
        assert v2 == "guest"
        assert user["role"] == "guest"

        events = _find_dict_events(user)
        assert len(events) == 3
        # First setdefault: inserted True
        assert events[1]["inputs"]["inserted"] is True
        # Second setdefault: inserted False
        assert events[2]["inputs"]["inserted"] is False


def test_dict_clear():
    with why.watch():
        user = why.track({"name": "Ali", "age": 20})
        user.clear()

        assert len(user) == 0
        events = _find_dict_events(user)
        assert len(events) == 2
        assert events[1]["event_type"] == "dict_clear"


def test_chronological_repeated_changes_to_same_key():
    with why.watch():
        user = why.track({"age": 20})
        user["age"] = 21
        user["age"] = 22

        age_events = _find_dict_events(user, key="age")
        assert len(age_events) == 3
        assert age_events[0]["event_type"] == "dict_created"
        assert age_events[1]["inputs"]["value"] == 21
        assert age_events[2]["inputs"]["value"] == 22


def test_snapshot_mutation_isolation():
    with why.watch(snapshot=True):
        user = why.track({"age": 20})
        user["age"] = 21
        user["age"] = 22

        events = _find_dict_events(user)
        assert events[1].before_value == {"age": 20}
        assert events[1].after_value == {"age": 21}

        # Further mutate user dict
        user["age"] = 99

        # Stored snapshot remains isolated
        assert events[1].after_value == {"age": 21}


def test_whole_dict_explain(capsys):
    with why.watch():
        user = why.track({"name": "Ali", "age": 20})
        user["age"] = 21

        why.explain(user)
        captured = capsys.readouterr().out

        assert "Why is this dict {'name': 'Ali', 'age': 21}?" in captured
        assert "1. Created dict {'name': 'Ali', 'age': 20}" in captured
        assert "2. age = 21" in captured


def test_key_specific_full_explain(capsys):
    with why.watch(snapshot=True):
        user = why.track({"name": "Ali", "age": 20})
        user["age"] = 21
        user["age"] = 22

        why.explain(user, key="age", mode="full")
        captured = capsys.readouterr().out

        assert "Why is age = 22?" in captured
        assert "1. Original: age = 20" in captured
        assert "2. set age = 21" in captured
        assert "3. set age = 22" in captured
        assert "Final:\nage = 22" in captured


def test_key_specific_short_explain(capsys):
    with why.watch():
        user = why.track({"age": 20})
        user["age"] = 21

        res = why.explain(user, key="age", mode="short")
        captured = capsys.readouterr().out

        expected = "age: Original: age = 20, set age = 21 → final: 21"
        assert res == expected
        assert expected in captured


def test_key_specific_json_explain():
    with why.watch(snapshot=True):
        user = why.track({"age": 20})
        user["age"] = 21

        data = why.explain(user, key="age", mode="json")

        assert isinstance(data, dict)
        assert data["object_type"] == "dict"
        assert data["key"] == "age"
        assert data["final_value"] == 21
        assert len(data["steps"]) == 2
        assert data["steps"][1]["event_type"] == "dict_setitem"
        assert data["steps"][1]["before"] == 20
        assert data["steps"][1]["after"] == 21


def test_snapshot_false_graceful_behavior(capsys):
    with why.watch(snapshot=False):
        user = why.track({"age": 20})
        user["age"] = 21

        why.explain(user, key="age", mode="full")
        captured = capsys.readouterr().out

        assert "Why is age = 21?" in captured
        assert "1. Original: age = 20" in captured
        assert "2. set age = 21" in captured

        events = _find_dict_events(user)
        assert events[1].before_value is None
        assert events[1].after_value is None


def test_list_and_pandas_unaffected():
    with why.watch():
        items = why.track([1, 2])
        items.append(3)

        user = why.track({"a": 10})
        user["a"] = 20

        df = pd.DataFrame({"col": [1.0, None]})
        df["col"] = df["col"].fillna(0.0)

        assert len(history.get_all()) == 5
        why.explain(items)
        why.explain(user)
        why.explain(df, 1, "col")


def test_unsupported_object_types_still_fail():
    with why.watch():
        for unsupported in (42, 3.14, "hello", (1, 2), {1, 2}):
            with pytest.raises(
                TypeError,
                match="WhyValue tracking does not support this object type yet.",
            ):
                why.track(unsupported)


def test_track_outside_watch_still_fails():
    assert why.is_watching() is False
    with pytest.raises(
        RuntimeError,
        match=r"why\.track\(\) requires an active WhyValue watch session\.",
    ):
        why.track({"a": 1})
