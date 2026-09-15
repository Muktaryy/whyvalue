from unittest.mock import MagicMock, patch
import pandas as pd
import pytest
import requests
import whyvalue as why
from whyvalue.history import history


def test_to_dataframe_outside_watch_raises():
    with pytest.raises(RuntimeError, match="requires an active WhyValue watch session"):
        why.to_dataframe([{"a": 1}])


def test_to_dataframe_unsupported_input_raises():
    with why.watch():
        with pytest.raises(TypeError, match="expects a tracked object"):
            why.to_dataframe(123)

        with pytest.raises(TypeError, match="expects a tracked object"):
            why.to_dataframe((x for x in range(5)))


def test_to_dataframe_tracked_list_and_tracked_dict_returns_pandas_df():
    with why.watch():
        tracked_list = why.track([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
        df_list = why.to_dataframe(tracked_list)

        assert isinstance(df_list, pd.DataFrame)
        assert len(df_list) == 2
        assert list(df_list.columns) == ["a", "b"]

        tracked_dict = why.track({"a": [1, 2], "b": [3, 4]})
        df_dict = why.to_dataframe(tracked_dict)

        assert isinstance(df_dict, pd.DataFrame)
        assert len(df_dict) == 2


def test_fresh_dataframe_identity_and_bridge_event():
    with why.watch():
        tracked_list = why.track([{"a": 10}])
        source_id = tracked_list._whyvalue_id

        df = why.to_dataframe(tracked_list)
        df_id = df.attrs["_whyvalue_id"]

        assert df_id != source_id
        assert df.attrs["_whyvalue_source_id"] == source_id

        events = history.get_all()
        bridge_events = [e for e in events if e.get("event_type") == "to_dataframe"]
        assert len(bridge_events) == 1
        assert bridge_events[0]["dataframe_id"] == df_id
        assert bridge_events[0]["source_id"] == source_id
        assert bridge_events[0]["inputs"]["columns"] == ["a"]
        assert bridge_events[0]["inputs"]["row_count"] == 1


def test_csv_to_dataframe_lineage_and_explain(tmp_path, capsys):
    csv_file = tmp_path / "users.csv"
    csv_file.write_text("name,age\nAli,21\nAmina,24\n", encoding="utf-8")

    with why.watch(snapshot=True):
        rows = why.load_csv(csv_file)
        df = why.to_dataframe(rows)

        # Source column explain
        why.explain(df, row=0, column="age")
        out1 = capsys.readouterr().out
        assert "Why is age = 21?" in out1
        assert "Source:" in out1
        assert str(csv_file) in out1
        assert "Format:" in out1
        assert "CSV" in out1
        assert "Source row:" in out1
        assert "1" in out1

        # Transformations after bridge
        df["age"] = df["age"].astype(int)
        df["next_age"] = df["age"] + 1

        why.explain(df, row=0, column="next_age")
        out2 = capsys.readouterr().out
        assert "Why is next_age = 22?" in out2
        assert "Source:" in out2
        assert str(csv_file) in out2
        assert "Transformations:" in out2
        assert "next_age" in out2


def test_json_to_dataframe_lineage_and_explain(tmp_path, capsys):
    json_file = tmp_path / "users.json"
    json_file.write_text('{"users": [{"name": "Ali", "age": 21}]}', encoding="utf-8")

    with why.watch():
        data = why.load_json(json_file)
        users = data["users"]
        df = why.to_dataframe(users)

        why.explain(df, row=0, column="age")
        out = capsys.readouterr().out

        assert "Why is age = 21?" in out
        assert "Source:" in out
        assert str(json_file) in out
        assert "Format:" in out
        assert "JSON" in out
        assert "Path:" in out
        assert "$.users[0].age" in out


@patch("requests.get")
def test_http_json_to_dataframe_lineage_and_explain(mock_requests_get, capsys):
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 200
    mock_resp.url = "https://api.example.com/users?token=SECRET"
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.json.return_value = {"users": [{"name": "Ali", "age": 21}]}
    mock_requests_get.return_value = mock_resp

    with why.watch():
        response = why.get("https://api.example.com/users?token=SECRET")
        data = response.json()
        users = data["users"]
        df = why.to_dataframe(users)

        why.explain(df, row=0, column="name")
        out = capsys.readouterr().out

        assert "Why is name = Ali?" in out
        assert "Source:" in out
        assert "GET https://api.example.com/users?token=REDACTED" in out
        assert "Status:" in out
        assert "200" in out
        assert "Path:" in out
        assert "$.users[0].name" in out


def test_manual_tracked_list_to_dataframe(capsys):
    with why.watch():
        rows = why.track([{"name": "Ali", "age": 21}])
        df = why.to_dataframe(rows)

        why.explain(df, row=0, column="name")
        out = capsys.readouterr().out

        assert "Why is name = Ali?" in out
        assert "Format:" in out
        assert "Python object" in out


def test_to_dataframe_explain_short_and_json_modes(tmp_path, capsys):
    csv_file = tmp_path / "users.csv"
    csv_file.write_text("name,age\nAli,21\n", encoding="utf-8")

    with why.watch():
        rows = why.load_csv(csv_file)
        df = why.to_dataframe(rows)

        # short mode
        why.explain(df, row=0, column="age", mode="short")
        short_out = capsys.readouterr().out
        assert "age: from CSV" in short_out

        # json mode
        json_data = why.explain(df, row=0, column="age", mode="json")
        assert isinstance(json_data, dict)
        assert json_data["column"] == "age"
        assert json_data["source"]["source_type"] == "csv"
        assert json_data["source"]["csv_row"] == 1


def test_original_tracked_source_remains_usable_after_to_dataframe(tmp_path):
    csv_file = tmp_path / "users.csv"
    csv_file.write_text("name,age\nAli,21\n", encoding="utf-8")

    with why.watch():
        rows = why.load_csv(csv_file)
        df = why.to_dataframe(rows)

        # Both tracked list and dataframe remain usable
        assert rows[0]["name"] == "Ali"
        assert df.loc[0, "name"] == "Ali"
        assert rows._whyvalue_id != df.attrs["_whyvalue_id"]
