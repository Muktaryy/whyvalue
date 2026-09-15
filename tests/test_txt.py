import pytest
import pandas as pd
import whyvalue as why
from whyvalue.adapters.python_list import TrackedList
from whyvalue.history import history


def test_load_txt_outside_watch_session_raises(tmp_path):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("hello\nworld\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="requires an active WhyValue watch session"):
        why.load_txt(txt_file)


def test_load_txt_returns_tracked_list_of_strings(tmp_path):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text(
        "Python is useful.\nSQL is useful.\nData engineering is fun.", encoding="utf-8"
    )

    with why.watch():
        lines = why.load_txt(txt_file)

        assert isinstance(lines, list)
        assert isinstance(lines, TrackedList)
        assert len(lines) == 3

        assert isinstance(lines[0], str)
        assert lines[0] == "Python is useful."
        assert isinstance(lines[1], str)
        assert lines[1] == "SQL is useful."
        assert isinstance(lines[2], str)
        assert lines[2] == "Data engineering is fun."


def test_load_txt_stable_object_id_and_txt_loaded_event(tmp_path):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("line1\nline2\n", encoding="utf-8")

    with why.watch():
        lines = why.load_txt(txt_file)

        assert hasattr(lines, "_whyvalue_id")
        obj_id = lines._whyvalue_id

        events = history.get_all()
        txt_events = [e for e in events if e.get("event_type") == "txt_loaded"]
        assert len(txt_events) == 1
        assert txt_events[0]["object_id"] == obj_id
        assert txt_events[0]["metadata"]["source_path"] == str(txt_file)
        assert txt_events[0]["metadata"]["line_count"] == 2
        assert txt_events[0]["metadata"]["encoding"] == "utf-8"
        assert txt_events[0]["metadata"]["keepends"] is False


def test_load_txt_keepends_false_and_true(tmp_path):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text("hello\nworld\n", encoding="utf-8")

    with why.watch():
        lines_no_ends = why.load_txt(txt_file, keepends=False)
        assert lines_no_ends == ["hello", "world"]

    with why.watch():
        lines_with_ends = why.load_txt(txt_file, keepends=True)
        assert lines_with_ends == ["hello\n", "world\n"]


def test_load_txt_empty_file(tmp_path):
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text("", encoding="utf-8")

    with why.watch():
        lines = why.load_txt(empty_file)
        assert isinstance(lines, TrackedList)
        assert len(lines) == 0


def test_load_txt_blank_lines_and_final_newline(tmp_path):
    txt_file = tmp_path / "blank.txt"
    txt_file.write_text("line1\n\nline3\n", encoding="utf-8")

    with why.watch():
        lines = why.load_txt(txt_file)
        assert len(lines) == 3
        assert lines[0] == "line1"
        assert lines[1] == ""
        assert lines[2] == "line3"


def test_load_txt_utf8_text(tmp_path):
    txt_file = tmp_path / "utf8.txt"
    txt_file.write_text("Mölnlycke\nGöteborg\nStockholm", encoding="utf-8")

    with why.watch():
        lines = why.load_txt(txt_file, encoding="utf-8")
        assert lines[0] == "Mölnlycke"
        assert lines[1] == "Göteborg"


def test_load_txt_file_not_found(tmp_path):
    missing_file = tmp_path / "non_existent.txt"

    with why.watch():
        with pytest.raises(FileNotFoundError):
            why.load_txt(missing_file)


def test_load_txt_encoding_error(tmp_path):
    latin_file = tmp_path / "latin.txt"
    latin_file.write_bytes("René\n".encode("latin-1"))

    with why.watch():
        with pytest.raises(UnicodeDecodeError):
            why.load_txt(latin_file, encoding="utf-8")


def test_txt_whole_file_explain(tmp_path, capsys):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text(
        "Python is useful.\nSQL is useful.\nData engineering is fun.", encoding="utf-8"
    )

    with why.watch():
        lines = why.load_txt(txt_file)

        # Full mode
        why.explain(lines, mode="full")
        full_out = capsys.readouterr().out
        assert "Why is this list" in full_out
        assert "Source:" in full_out
        assert str(txt_file) in full_out
        assert "Format:" in full_out
        assert "TXT" in full_out
        assert "Lines:" in full_out
        assert "3" in full_out

        # Short mode
        why.explain(lines, mode="short")
        short_out = capsys.readouterr().out
        assert "list: from TXT" in short_out
        assert str(txt_file) in short_out

        # JSON mode
        json_data = why.explain(lines, mode="json")
        assert isinstance(json_data, dict)
        assert json_data["object_type"] == "list"
        assert json_data["source"]["source_type"] == "txt"
        assert json_data["source"]["line_count"] == 3


def test_txt_line_specific_explain(tmp_path, capsys):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text(
        "Python is useful.\nSQL is useful.\nData engineering is fun.", encoding="utf-8"
    )

    with why.watch():
        lines = why.load_txt(txt_file)

        # Line-specific full mode (index=1 -> line 2)
        why.explain(lines, index=1, mode="full")
        full_out = capsys.readouterr().out
        assert 'Why is line 2 = "SQL is useful."' in full_out
        assert "Source:" in full_out
        assert str(txt_file) in full_out
        assert "Format:" in full_out
        assert "TXT" in full_out
        assert "Line:" in full_out
        assert "2" in full_out
        assert "Original:" in full_out
        assert '"SQL is useful."' in full_out
        assert "Final:" in full_out

        # Line-specific short mode
        why.explain(lines, index=1, mode="short")
        short_out = capsys.readouterr().out
        assert "line 2: from TXT" in short_out

        # Line-specific JSON mode
        json_data = why.explain(lines, index=1, mode="json")
        assert isinstance(json_data, dict)
        assert json_data["object_type"] == "txt"
        assert json_data["index"] == 1
        assert json_data["final_value"] == "SQL is useful."
        assert json_data["source"]["source_type"] == "txt"
        assert json_data["source"]["line"] == 2


def test_txt_mutation_after_load_snapshot_true(tmp_path, capsys):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text(
        "Python is useful.\nSQL is useful.\nData engineering is fun.", encoding="utf-8"
    )

    with why.watch(snapshot=True):
        lines = why.load_txt(txt_file)
        lines[1] = "SQL is very useful."

        why.explain(lines, index=1)
        captured = capsys.readouterr().out

        assert 'Why is line 2 = "SQL is very useful."' in captured
        assert "Source:" in captured
        assert str(txt_file) in captured
        assert "Line:" in captured
        assert "2" in captured
        assert "Transformation history:" in captured
        assert 'Original: "SQL is useful."' in captured
        assert "[1] = SQL is very useful." in captured
        assert "Final:" in captured
        assert '"SQL is very useful."' in captured


def test_txt_mutation_after_load_snapshot_false(tmp_path, capsys):
    txt_file = tmp_path / "notes.txt"
    txt_file.write_text(
        "Python is useful.\nSQL is useful.\nData engineering is fun.", encoding="utf-8"
    )

    with why.watch(snapshot=False):
        lines = why.load_txt(txt_file)
        lines[1] = "SQL is very useful."

        why.explain(lines, index=1)
        captured = capsys.readouterr().out

        assert 'Why is line 2 = "SQL is very useful."' in captured
        assert 'Original: "SQL is useful."' in captured
        assert "[1] = SQL is very useful." in captured


def test_no_regression_existing_features(tmp_path):
    # JSON unaffected
    j_file = tmp_path / "data.json"
    j_file.write_text('{"key": "val"}', encoding="utf-8")

    # CSV unaffected
    c_file = tmp_path / "data.csv"
    c_file.write_text("col\nval\n", encoding="utf-8")

    with why.watch():
        j_data = why.load_json(j_file)
        c_data = why.load_csv(c_file)
        p_list = why.track([1, 2, 3])
        df = pd.DataFrame({"a": [10, 20]})

        assert j_data["key"] == "val"
        assert c_data[0]["col"] == "val"
        assert p_list == [1, 2, 3]
        assert len(df) == 2
