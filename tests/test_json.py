import json
import pandas as pd
import pytest

import whyvalue as why
from whyvalue.adapters.python_dict import TrackedDict
from whyvalue.adapters.python_list import TrackedList
from whyvalue.history import history


def test_load_root_json_dict(tmp_path):
    json_file = tmp_path / "user.json"
    json_file.write_text('{"name": "Ali", "age": 21}', encoding="utf-8")

    with why.watch():
        data = why.load_json(json_file)

        assert isinstance(data, dict)
        assert isinstance(data, TrackedDict)
        assert data["name"] == "Ali"
        assert data["age"] == 21


def test_load_root_json_list(tmp_path):
    json_file = tmp_path / "numbers.json"
    json_file.write_text("[10, 20, 30]", encoding="utf-8")

    with why.watch():
        data = why.load_json(json_file)

        assert isinstance(data, list)
        assert isinstance(data, TrackedList)
        assert data == [10, 20, 30]


def test_nested_dict_and_list_tracking(tmp_path):
    payload = {
        "users": [
            {"name": "Ali", "age": 21},
            {"name": "Amina", "age": 24},
        ]
    }
    json_file = tmp_path / "users.json"
    json_file.write_text(json.dumps(payload), encoding="utf-8")

    with why.watch():
        data = why.load_json(json_file)

        assert isinstance(data, TrackedDict)
        assert isinstance(data["users"], TrackedList)
        assert isinstance(data["users"][0], TrackedDict)
        assert isinstance(data["users"][1], TrackedDict)


def test_stable_object_ids_and_json_loaded_events(tmp_path):
    json_file = tmp_path / "data.json"
    json_file.write_text('{"user": {"name": "Ali"}}', encoding="utf-8")

    with why.watch():
        data = why.load_json(json_file)
        nested_user = data["user"]

        assert hasattr(data, "_whyvalue_id")
        assert hasattr(nested_user, "_whyvalue_id")
        assert data._whyvalue_id != nested_user._whyvalue_id

        events = history.get_all()
        loaded_events = [e for e in events if e.get("event_type") == "json_loaded"]
        assert len(loaded_events) == 2


def test_json_path_metadata(tmp_path):
    test_json_paths = '{"config": {"items": [{"id": 100}]}}'
    json_file = tmp_path / "config.json"
    json_file.write_text(test_json_paths, encoding="utf-8")

    with why.watch():
        data = why.load_json(json_file)

        assert data._whyvalue_source["json_path"] == "$"
        assert data["config"]._whyvalue_source["json_path"] == "$.config"
        assert data["config"]["items"]._whyvalue_source["json_path"] == "$.config.items"
        assert (
            data["config"]["items"][0]._whyvalue_source["json_path"]
            == "$.config.items[0]"
        )


def test_key_specific_explain_includes_source(tmp_path, capsys):
    json_file = tmp_path / "user.json"
    json_file.write_text('{"name": "Ali", "age": 21}', encoding="utf-8")

    with why.watch():
        data = why.load_json(json_file)

        why.explain(data, key="age")
        captured = capsys.readouterr().out

        assert "Why is age = 21?" in captured
        assert "Source:\n" in captured
        assert str(json_file) in captured
        assert "Format:\nJSON" in captured
        assert "Path:\n$.age" in captured
        assert "Original:\nage = 21" in captured
        assert "Final:\nage = 21" in captured


def test_nested_explain_includes_correct_source_path(tmp_path, capsys):
    payload = {"users": [{"name": "Ali", "age": 21}]}
    json_file = tmp_path / "users.json"
    json_file.write_text(json.dumps(payload), encoding="utf-8")

    with why.watch():
        data = why.load_json(json_file)
        user = data["users"][0]

        why.explain(user, key="name")
        captured = capsys.readouterr().out

        assert "Why is name = Ali?" in captured
        assert "Path:\n$.users[0].name" in captured
        assert "Original:\nname = Ali" in captured


def test_mutation_after_json_load_continues_provenance(tmp_path, capsys):
    payload = {"users": [{"name": "Ali", "age": 21}]}
    json_file = tmp_path / "users.json"
    json_file.write_text(json.dumps(payload), encoding="utf-8")

    with why.watch():
        data = why.load_json(json_file)
        user = data["users"][0]
        user["age"] = 22

        why.explain(user, key="age")
        captured = capsys.readouterr().out

        assert "Why is age = 22?" in captured
        assert "Path:\n$.users[0].age" in captured
        assert "Transformation history:" in captured
        assert "1. Original: age = 21" in captured
        assert "2. set age = 22" in captured
        assert "Final:\nage = 22" in captured


def test_snapshot_true_mutation_history(tmp_path):
    json_file = tmp_path / "user.json"
    json_file.write_text('{"age": 20}', encoding="utf-8")

    with why.watch(snapshot=True):
        user = why.load_json(json_file)
        user["age"] = 21

        data = why.explain(user, key="age", mode="json")

        assert data["source"]["source_type"] == "json"
        assert data["source"]["json_path"] == "$.age"
        assert data["steps"][1]["before"] == 20
        assert data["steps"][1]["after"] == 21


def test_json_explain_modes(tmp_path, capsys):
    json_file = tmp_path / "user.json"
    json_file.write_text('{"name": "Ali"}', encoding="utf-8")

    with why.watch():
        user = why.load_json(json_file)

        # mode="short"
        short_res = why.explain(user, key="name", mode="short")
        captured = capsys.readouterr().out
        assert "name: from JSON" in short_res

        # mode="json"
        json_res = why.explain(user, key="name", mode="json")
        assert isinstance(json_res, dict)
        assert json_res["source"]["source_type"] == "json"
        assert json_res["source"]["json_path"] == "$.name"


def test_file_encoding(tmp_path):
    json_file = tmp_path / "latin.json"
    json_file.write_text('{"city": "München"}', encoding="utf-8")

    with why.watch():
        data = why.load_json(json_file, encoding="utf-8")
        assert data["city"] == "München"


def test_file_not_found_error():
    with why.watch():
        with pytest.raises(FileNotFoundError):
            why.load_json("nonexistent_file_123.json")


def test_invalid_json_decode_error(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid json", encoding="utf-8")

    with why.watch():
        with pytest.raises(json.JSONDecodeError):
            why.load_json(bad_file)


def test_load_json_outside_watch_fails():
    assert why.is_watching() is False
    with pytest.raises(
        RuntimeError,
        match=r"why\.load_json\(\) requires an active WhyValue watch session\.",
    ):
        why.load_json("some.json")


def test_list_dict_pandas_unaffected(tmp_path):
    json_file = tmp_path / "test.json"
    json_file.write_text('{"x": 1}', encoding="utf-8")

    with why.watch():
        j_data = why.load_json(json_file)

        t_list = why.track([10, 20])
        t_list.append(30)

        t_dict = why.track({"a": 1})
        t_dict["a"] = 2

        df = pd.DataFrame({"col": [1.0, None]})
        df["col"] = df["col"].fillna(0.0)

        why.explain(j_data, key="x")
        why.explain(t_list)
        why.explain(t_dict, key="a")
        why.explain(df, 1, "col")
