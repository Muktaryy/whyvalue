import pandas as pd
import pytest
import whyvalue as why


def test_explain_default_backwards_compatible(capsys):
    why.watch()
    df = pd.DataFrame({"price": [10, None, 30]})
    df["price"] = df["price"].fillna(0)

    why.explain(df, row=1, column="price")
    out = capsys.readouterr().out

    assert "Why is price = 0" in out
    assert "Original value:" in out
    assert "NaN" in out
    assert "Transformation:" in out
    assert "fillna(0)" in out
    assert "NaN → 0" in out

    why.stop()


def test_explain_mode_full_uses_fillna_snapshots(capsys):
    why.watch(snapshot=True)
    df = pd.DataFrame({"price": [10, None, 30]})
    df["price"] = df["price"].fillna(0)

    why.explain(df, row=1, column="price", mode="full")
    out = capsys.readouterr().out

    assert "Why is price = 0" in out
    assert "Original:" in out
    assert "price = NaN" in out
    assert "Operation:" in out
    assert "fillna(0)" in out
    assert "Before:" in out
    assert "NaN" in out
    assert "After:" in out
    assert "0" in out
    assert "Final:" in out
    assert "price = 0" in out

    why.stop()


def test_explain_mode_full_snapshot_mutation_isolation(capsys):
    why.watch(snapshot=True)
    df = pd.DataFrame({"price": [10, None, 30]})
    df["price"] = df["price"].fillna(0)

    # Mutate DataFrame after fillna
    df["price"] = [999, 999, 999]
    df.loc[1, "price"] = 777

    why.explain(df, row=1, column="price", mode="full")
    out = capsys.readouterr().out

    # Current value is 777, but snapshots preserve historical before/after
    assert "Why is price = 777" in out
    assert "Original:" in out
    assert "price = NaN" in out
    assert "Before:" in out
    assert "NaN" in out
    assert "After:" in out
    assert "0" in out
    assert "Final:" in out
    assert "price = 777" in out

    why.stop()


def test_explain_mode_short(capsys):
    why.watch(snapshot=True)
    capsys.readouterr()  # Clear watch() output
    df = pd.DataFrame({"price": [10, None, 30]})
    df["price"] = df["price"].fillna(0)

    short_out = why.explain(df, row=1, column="price", mode="short")
    printed_out = capsys.readouterr().out.strip()

    assert "price: NaN → 0" in short_out
    assert "fillna(0)" in short_out
    assert printed_out == short_out

    why.stop()


def test_explain_mode_json_returns_dict():
    why.watch(snapshot=True)
    df = pd.DataFrame({"price": [10, None, 30]})
    df["price"] = df["price"].fillna(0)

    data = why.explain(df, row=1, column="price", mode="json")

    assert isinstance(data, dict)
    assert data["column"] == "price"
    assert data["row"] == 1
    assert data["final_value"] == 0
    assert len(data["steps"]) == 1
    assert data["steps"][0]["operation"] == "fillna"
    assert data["steps"][0]["before"] is None
    assert data["steps"][0]["after"] == 0

    why.stop()


def test_explain_snapshot_false_graceful_full_mode(capsys):
    why.watch(snapshot=False)
    df = pd.DataFrame({"price": [10, None, 30]})
    df["price"] = df["price"].fillna(0)

    why.explain(df, row=1, column="price", mode="full")
    out = capsys.readouterr().out

    assert "Why is price = 0" in out
    assert "Original value:" in out
    assert "Transformation:" in out
    assert "Before:" not in out

    why.stop()


def test_explain_invalid_mode_raises_value_error():
    why.watch()
    df = pd.DataFrame({"price": [10]})
    df["double"] = df["price"] * 2

    with pytest.raises(ValueError, match="mode must be 'short', 'full', or 'json'"):
        why.explain(df, row=0, column="double", mode="invalid")

    why.stop()
