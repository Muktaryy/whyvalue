import pytest
import whyvalue as why
from whyvalue.adapters.python_dict import TrackedDict
from whyvalue.adapters.python_list import TrackedList
from whyvalue.history import history


def test_load_csv_outside_watch_session_raises(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("name,age\nAli,21\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="requires an active WhyValue watch session"):
        why.load_csv(csv_file)


def test_load_csv_basic(tmp_path):
    csv_file = tmp_path / "users.csv"
    csv_file.write_text(
        "name,age,city\nAli,21,Stockholm\nAmina,24,Gothenburg\n", encoding="utf-8"
    )

    with why.watch():
        rows = why.load_csv(csv_file)

        assert isinstance(rows, TrackedList)
        assert len(rows) == 2

        user0 = rows[0]
        assert isinstance(user0, TrackedDict)
        assert user0["name"] == "Ali"
        assert user0["age"] == "21"
        assert user0["city"] == "Stockholm"

        user1 = rows[1]
        assert isinstance(user1, TrackedDict)
        assert user1["name"] == "Amina"
        assert user1["age"] == "24"
        assert user1["city"] == "Gothenburg"


def test_load_csv_strings_no_type_inference(tmp_path):
    csv_file = tmp_path / "types.csv"
    csv_file.write_text("id,score,active\n100,98.5,True\n", encoding="utf-8")

    with why.watch():
        rows = why.load_csv(csv_file)
        row = rows[0]

        assert isinstance(row["id"], str)
        assert row["id"] == "100"
        assert isinstance(row["score"], str)
        assert row["score"] == "98.5"
        assert isinstance(row["active"], str)
        assert row["active"] == "True"


def test_load_csv_no_fake_mutation_events(tmp_path):
    csv_file = tmp_path / "users.csv"
    csv_file.write_text("name,age\nAli,21\nAmina,24\n", encoding="utf-8")

    with why.watch():
        rows = why.load_csv(csv_file)
        _ = rows[0]

        events = history.get_all()
        event_types = [e.get("event_type") for e in events]

        assert "dict_setitem" not in event_types
        assert "list_append" not in event_types
        # 2 row dict events + 1 list event
        assert len(event_types) == 3
        assert all(et == "csv_loaded" for et in event_types)


def test_load_csv_row_numbering(tmp_path):
    csv_file = tmp_path / "users.csv"
    csv_file.write_text("name,age\nAli,21\nAmina,24\n", encoding="utf-8")

    with why.watch():
        rows = why.load_csv(csv_file)

        assert rows[0]._whyvalue_source["csv_row"] == 1
        assert rows[1]._whyvalue_source["csv_row"] == 2


def test_load_csv_custom_delimiter_and_encoding(tmp_path):
    csv_file = tmp_path / "custom.csv"
    csv_file.write_text("name;age;city\nBjörn;30;Mölnlycke\n", encoding="utf-8")

    with why.watch():
        rows = why.load_csv(csv_file, delimiter=";", encoding="utf-8")

        assert len(rows) == 1
        assert rows[0]["name"] == "Björn"
        assert rows[0]["age"] == "30"
        assert rows[0]["city"] == "Mölnlycke"
        assert rows[0]._whyvalue_source["delimiter"] == ";"


def test_load_csv_headers_only(tmp_path):
    csv_file = tmp_path / "empty.csv"
    csv_file.write_text("name,age,city\n", encoding="utf-8")

    with why.watch():
        rows = why.load_csv(csv_file)

        assert isinstance(rows, TrackedList)
        assert len(rows) == 0


def test_load_csv_file_not_found(tmp_path):
    missing_file = tmp_path / "non_existent.csv"

    with why.watch():
        with pytest.raises(FileNotFoundError):
            why.load_csv(missing_file)


def test_load_csv_encoding_error(tmp_path):
    csv_file = tmp_path / "latin1.csv"
    csv_file.write_bytes("name,city\nRené,München\n".encode("latin-1"))

    with why.watch():
        with pytest.raises(UnicodeDecodeError):
            why.load_csv(csv_file, encoding="utf-8")


def test_csv_explain_row_key(tmp_path, capsys):
    csv_file = tmp_path / "users.csv"
    csv_file.write_text("name,age\nAli,21\n", encoding="utf-8")

    with why.watch():
        rows = why.load_csv(csv_file)
        user = rows[0]

        why.explain(user, key="age")
        captured = capsys.readouterr().out

        assert "Why is age = 21?" in captured
        assert "Source:" in captured
        assert str(csv_file) in captured
        assert "Format:" in captured
        assert "CSV" in captured
        assert "Row:" in captured
        assert "1" in captured
        assert "Column:" in captured
        assert "age" in captured
        assert "Original:" in captured
        assert "age = 21" in captured
        assert "Final:" in captured


def test_csv_explain_modes(tmp_path, capsys):
    csv_file = tmp_path / "users.csv"
    csv_file.write_text("name,age\nAli,21\n", encoding="utf-8")

    with why.watch():
        rows = why.load_csv(csv_file)
        user = rows[0]

        # full mode
        why.explain(user, key="age", mode="full")
        full_out = capsys.readouterr().out
        assert "Why is age = 21?" in full_out
        assert "Source:" in full_out

        # short mode
        why.explain(user, key="age", mode="short")
        short_out = capsys.readouterr().out
        assert "age = 21" in short_out
        assert "from CSV" in short_out

        # json mode
        data = why.explain(user, key="age", mode="json")
        assert isinstance(data, dict)
        assert data["key"] == "age"
        assert data["source"]["source_type"] == "csv"
        assert data["source"]["csv_row"] == 1
        assert data["source"]["csv_column"] == "age"


def test_csv_mutation_after_load_explain(tmp_path, capsys):
    csv_file = tmp_path / "users.csv"
    csv_file.write_text("name,age\nAli,21\n", encoding="utf-8")

    with why.watch(snapshot=True):
        rows = why.load_csv(csv_file)
        user = rows[0]

        user["age"] = "22"

        why.explain(user, key="age")
        captured = capsys.readouterr().out

        assert "Why is age = 22?" in captured
        assert "Transformation history:" in captured
        assert "Original: age = 21" in captured
        assert "set age = 22" in captured
        assert "Final:" in captured
        assert "age = 22" in captured


def test_csv_list_explain(tmp_path, capsys):
    csv_file = tmp_path / "users.csv"
    csv_file.write_text("name,age\nAli,21\nAmina,24\n", encoding="utf-8")

    with why.watch():
        rows = why.load_csv(csv_file)

        why.explain(rows)
        captured = capsys.readouterr().out

        assert "Why is this list" in captured
        assert "Source:" in captured
        assert str(csv_file) in captured
        assert "Format:" in captured
        assert "CSV" in captured
