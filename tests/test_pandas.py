import pandas as pd
import pytest
import whyvalue as why

from whyvalue.history import history
from whyvalue.core import (
    _get_dataframe_id,
    _event_matches_dataframe,
    _find_event,
    _find_events,
)

from whyvalue.adapters.pandas import _get_dataframe_id as _get_adapter_dataframe_id


@pytest.fixture(autouse=True)
def clean_whyvalue_state():
    why.stop()
    history.clear()

    try:
        yield
    finally:
        why.stop()
        history.clear()


def test_multiplication_is_recorded():

    why.watch()

    df = pd.DataFrame(
        {
            "price": [100, 200, 300],
            "quantity": [2, 3, 4],
        }
    )

    df["revenue"] = df["price"] * df["quantity"]

    events = history.get_all()

    why.stop()

    assert len(events) == 1
    assert events[0]["column"] == "revenue"
    assert events[0]["operation"] == "multiply"
    assert events[0]["left"] == "price"
    assert events[0]["right"] == "quantity"


def test_scalar_multiplication_is_recorded():
    why.watch()

    df = pd.DataFrame(
        {
            "revenue": [200, 600, 1200],
        }
    )

    df["tax"] = df["revenue"] * 0.25

    events = history.get_all()

    why.stop()

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "column_created"
    assert event["column"] == "tax"
    assert event["operation"] == "multiply"
    assert event["left"] == "revenue"
    assert event["right"] == 0.25
    assert event["right_type"] == "scalar"


def test_scalar_multiplication_is_traced_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "revenue": [200, 600, 1200],
        }
    )

    df["tax"] = df["revenue"] * 0.25

    why.trace(df)

    trace_output = capsys.readouterr().out

    assert "tax = revenue × 0.25" in trace_output

    why.explain(
        df,
        row=1,
        column="tax",
    )

    explain_output = capsys.readouterr().out

    why.stop()

    assert "Why is tax = 150.0?" in explain_output
    assert "revenue = 600" in explain_output
    assert "600 × 0.25" in explain_output
    assert "tax = 150.0" in explain_output


def test_subtraction_is_recorded():
    why.watch()

    df = pd.DataFrame(
        {
            "revenue": [200, 600, 1200],
            "cost": [50, 100, 250],
        }
    )

    df["profit"] = df["revenue"] - df["cost"]

    events = history.get_all()

    why.stop()

    assert len(events) == 1
    assert events[0]["column"] == "profit"
    assert events[0]["operation"] == "subtract"
    assert events[0]["left"] == "revenue"
    assert events[0]["right"] == "cost"


def test_addition_is_recorded_traced_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "salary": [3000, 4000, 5000],
            "bonus": [500, 700, 1000],
        }
    )

    df["total_pay"] = df["salary"] + df["bonus"]

    events = history.get_all()

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "column_created"
    assert event["column"] == "total_pay"
    assert event["operation"] == "add"
    assert event["left"] == "salary"
    assert event["right"] == "bonus"
    assert event["right_type"] == "column"

    why.trace(df)

    trace_output = capsys.readouterr().out

    assert "total_pay = salary + bonus" in trace_output

    why.explain(
        df,
        row=1,
        column="total_pay",
    )

    explain_output = capsys.readouterr().out

    why.stop()

    assert "Why is total_pay = 4700?" in explain_output
    assert "salary = 4000" in explain_output
    assert "bonus = 700" in explain_output
    assert "4000 + 700" in explain_output
    assert "total_pay = 4700" in explain_output


def test_scalar_addition_is_recorded_traced_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "price": [100, 200, 300],
        }
    )

    df["price_with_fee"] = df["price"] + 10

    events = history.get_all()

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "column_created"
    assert event["column"] == "price_with_fee"
    assert event["operation"] == "add"
    assert event["left"] == "price"
    assert event["right"] == 10
    assert event["right_type"] == "scalar"

    why.trace(df)

    trace_output = capsys.readouterr().out

    assert "price_with_fee = price + 10" in trace_output

    why.explain(
        df,
        row=1,
        column="price_with_fee",
    )

    explain_output = capsys.readouterr().out

    why.stop()

    assert "Why is price_with_fee = 210?" in explain_output
    assert "price = 200" in explain_output
    assert "200 + 10" in explain_output
    assert "price_with_fee = 210" in explain_output


def test_division_is_recorded_traced_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "revenue": [200, 600, 1200],
            "quantity": [2, 3, 4],
        }
    )

    df["average_price"] = df["revenue"] / df["quantity"]

    events = history.get_all()

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "column_created"
    assert event["column"] == "average_price"
    assert event["operation"] == "divide"
    assert event["left"] == "revenue"
    assert event["right"] == "quantity"
    assert event["right_type"] == "column"

    why.trace(df)

    trace_output = capsys.readouterr().out

    assert "average_price = revenue / quantity" in trace_output

    why.explain(
        df,
        row=1,
        column="average_price",
    )

    explain_output = capsys.readouterr().out

    why.stop()

    assert "Why is average_price = 200.0?" in explain_output
    assert "revenue = 600" in explain_output
    assert "quantity = 3" in explain_output
    assert "600 / 3" in explain_output
    assert "average_price = 200.0" in explain_output


def test_scalar_division_is_recorded_traced_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "price": [100, 200, 300],
        }
    )

    df["half_price"] = df["price"] / 2

    events = history.get_all()

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "column_created"
    assert event["column"] == "half_price"
    assert event["operation"] == "divide"
    assert event["left"] == "price"
    assert event["right"] == 2
    assert event["right_type"] == "scalar"

    why.trace(df)

    trace_output = capsys.readouterr().out

    assert "half_price = price / 2" in trace_output

    why.explain(
        df,
        row=1,
        column="half_price",
    )

    explain_output = capsys.readouterr().out

    why.stop()

    assert "Why is half_price = 100.0?" in explain_output
    assert "price = 200" in explain_output
    assert "200 / 2" in explain_output
    assert "half_price = 100.0" in explain_output


def test_reverse_addition_is_recorded_traced_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "price": [100, 200, 300],
        }
    )

    df["price_with_fee"] = 10 + df["price"]

    events = history.get_all()

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "column_created"
    assert event["column"] == "price_with_fee"
    assert event["operation"] == "add"
    assert event["left"] == 10
    assert event["left_type"] == "scalar"
    assert event["right"] == "price"
    assert event["right_type"] == "column"

    why.trace(df)

    trace_output = capsys.readouterr().out

    assert "price_with_fee = 10 + price" in trace_output

    why.explain(
        df,
        row=1,
        column="price_with_fee",
    )

    explain_output = capsys.readouterr().out

    why.stop()

    assert "Why is price_with_fee = 210?" in explain_output
    assert "price = 200" in explain_output
    assert "10 + 200" in explain_output
    assert "price_with_fee = 210" in explain_output


def test_scalar_subtraction_is_recorded_traced_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "price": [100, 200, 300],
        }
    )

    df["discounted_price"] = df["price"] - 10

    events = history.get_all()

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "column_created"
    assert event["column"] == "discounted_price"
    assert event["operation"] == "subtract"
    assert event["left"] == "price"
    assert event["right"] == 10
    assert event["right_type"] == "scalar"

    why.trace(df)

    trace_output = capsys.readouterr().out

    assert "discounted_price = price - 10" in trace_output

    why.explain(
        df,
        row=1,
        column="discounted_price",
    )

    explain_output = capsys.readouterr().out

    why.stop()

    assert "Why is discounted_price = 190?" in explain_output
    assert "price = 200" in explain_output
    assert "200 - 10" in explain_output
    assert "discounted_price = 190" in explain_output


def test_explain_follows_transformation_chain(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "price": [100, 200, 300],
            "quantity": [2, 3, 4],
            "cost": [50, 100, 250],
        }
    )

    df["revenue"] = df["price"] * df["quantity"]
    df["profit"] = df["revenue"] - df["cost"]

    why.explain(df, row=1, column="profit")

    output = capsys.readouterr().out

    why.stop()

    assert "Why is profit = 500?" in output
    assert "price = 200" in output
    assert "quantity = 3" in output
    assert "200 × 3" in output
    assert "revenue = 600" in output
    assert "cost = 100" in output
    assert "600 - 100" in output
    assert "profit = 500" in output


def test_fillna_is_recorded_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "name": ["Ali", "Ahmed", "Sara"],
            "age": [25, None, 17],
        }
    )

    df["age"] = df["age"].fillna(0)

    events = history.get_all()

    assert len(events) == 1
    assert events[0]["type"] == "column_filled"
    assert events[0]["column"] == "age"
    assert events[0]["operation"] == "fillna"
    assert events[0]["value"] == 0
    assert events[0]["missing_rows"] == [1]

    why.explain(df, row=1, column="age")

    output = capsys.readouterr().out

    why.stop()

    assert "Why is age = 0.0?" in output
    assert "Original value:" in output
    assert "NaN" in output
    assert "fillna(0)" in output
    assert "NaN → 0.0" in output


def test_removed_row_is_recorded_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "name": ["Ali", "Ahmed", "Sara"],
            "age": [25, None, 17],
        }
    )

    df["age"] = df["age"].fillna(0)
    df = df[df["age"] >= 18]

    events = history.get_all()

    assert len(events) == 2

    filter_event = events[1]

    assert filter_event["type"] == "filter"
    assert filter_event["column"] == "age"
    assert filter_event["operator"] == ">="
    assert filter_event["value"] == 18
    assert filter_event["removed_rows"] == [1, 2]
    assert filter_event["removed_values"][1] == 0.0
    assert filter_event["removed_values"][2] == 17.0

    why.explain_removed(df, row=1)

    output = capsys.readouterr().out

    why.stop()

    assert "Why was row 1 removed?" in output
    assert "Original age:" in output
    assert "NaN" in output
    assert "fillna(0)" in output
    assert "NaN → 0.0" in output
    assert "Filter:" in output
    assert "age >= 18" in output
    assert "0.0 >= 18 → False" in output
    assert "Row removed" in output


def test_dataframe_histories_do_not_mix(capsys):
    why.watch()

    customers = pd.DataFrame(
        {
            "name": ["Ali", "Sara"],
            "age": [None, 20],
        }
    )

    employees = pd.DataFrame(
        {
            "name": ["Ahmed", "Amina"],
            "age": [None, 40],
        }
    )

    customers["age"] = customers["age"].fillna(0)
    employees["age"] = employees["age"].fillna(99)

    why.trace(customers)

    customers_output = capsys.readouterr().out

    why.trace(employees)

    employees_output = capsys.readouterr().out

    why.stop()

    assert "age: missing values → 0" in customers_output
    assert "age: missing values → 99" not in customers_output

    assert "age: missing values → 99" in employees_output
    assert "age: missing values → 0" not in employees_output


@pytest.mark.parametrize(
    "operator, expected_removed_rows",
    [
        (">", [0, 1]),
        ("<", [2, 3]),
        ("<=", [3]),
        ("==", [0, 1, 3]),
        ("!=", [2]),
    ],
)
def test_filter_operators_are_recorded(
    operator,
    expected_removed_rows,
):
    why.watch()

    df = pd.DataFrame(
        {
            "age": [10, 18, 25, 30],
        }
    )

    if operator == ">":
        df = df[df["age"] > 18]

    elif operator == "<":
        df = df[df["age"] < 25]

    elif operator == "<=":
        df = df[df["age"] <= 25]

    elif operator == "==":
        df = df[df["age"] == 25]

    elif operator == "!=":
        df = df[df["age"] != 25]

    events = history.get_all()

    why.stop()

    assert len(events) == 1

    filter_event = events[0]

    assert filter_event["type"] == "filter"
    assert filter_event["column"] == "age"
    assert filter_event["operator"] == operator
    assert filter_event["removed_rows"] == expected_removed_rows


def test_reverse_subtraction_is_recorded_traced_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "cost": [100, 200, 300],
        }
    )

    df["remaining"] = 1000 - df["cost"]

    events = history.get_all()

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "column_created"
    assert event["column"] == "remaining"
    assert event["operation"] == "subtract"
    assert event["left"] == 1000
    assert event["left_type"] == "scalar"
    assert event["right"] == "cost"
    assert event["right_type"] == "column"

    why.trace(df)

    trace_output = capsys.readouterr().out

    assert "remaining = 1000 - cost" in trace_output

    why.explain(
        df,
        row=1,
        column="remaining",
    )

    explain_output = capsys.readouterr().out

    why.stop()

    assert "Why is remaining = 800?" in explain_output
    assert "cost = 200" in explain_output
    assert "1000 - 200" in explain_output
    assert "remaining = 800" in explain_output


def test_reverse_multiplication_is_recorded_traced_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "price": [100, 200, 300],
        }
    )

    df["double_price"] = 2 * df["price"]

    events = history.get_all()

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "column_created"
    assert event["column"] == "double_price"
    assert event["operation"] == "multiply"
    assert event["left"] == 2
    assert event["left_type"] == "scalar"
    assert event["right"] == "price"
    assert event["right_type"] == "column"

    why.trace(df)

    trace_output = capsys.readouterr().out

    assert "double_price = 2 × price" in trace_output

    why.explain(
        df,
        row=1,
        column="double_price",
    )

    explain_output = capsys.readouterr().out

    why.stop()

    assert "Why is double_price = 400?" in explain_output
    assert "price = 200" in explain_output
    assert "2 × 200" in explain_output
    assert "double_price = 400" in explain_output


def test_reverse_division_is_recorded_traced_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "price": [100, 200, 250],
        }
    )

    df["ratio"] = 1000 / df["price"]

    events = history.get_all()

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "column_created"
    assert event["column"] == "ratio"
    assert event["operation"] == "divide"
    assert event["left"] == 1000
    assert event["left_type"] == "scalar"
    assert event["right"] == "price"
    assert event["right_type"] == "column"

    why.trace(df)

    trace_output = capsys.readouterr().out

    assert "ratio = 1000 / price" in trace_output

    why.explain(
        df,
        row=1,
        column="ratio",
    )

    explain_output = capsys.readouterr().out

    why.stop()

    assert "Why is ratio = 5.0?" in explain_output
    assert "price = 200" in explain_output
    assert "1000 / 200" in explain_output
    assert "ratio = 5.0" in explain_output


def test_dropna_is_recorded_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "name": ["Ali", "Ahmed", "Sara"],
            "age": [25, None, 17],
        }
    )

    df = df.dropna(subset=["age"])

    events = history.get_all()

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "dropna"
    assert event["subset"] == ["age"]
    assert event["removed_rows"] == [1]

    why.explain_removed(df, row=1)

    output = capsys.readouterr().out

    why.stop()

    assert "Why was row 1 removed?" in output
    assert "dropna(subset=['age'])" in output
    assert "Row removed because required data was missing." in output


def test_combined_and_filter_is_recorded_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "age": [17, 20, 30],
            "salary": [5000, 2500, 4500],
        }
    )

    df = df[(df["age"] >= 18) & (df["salary"] > 3000)]

    events = history.get_all()

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "combined_filter"
    assert event["logic"] == "and"
    assert event["conditions"] == [
        {
            "column": "age",
            "operator": ">=",
            "value": 18,
        },
        {
            "column": "salary",
            "operator": ">",
            "value": 3000,
        },
    ]
    assert event["removed_rows"] == [0, 1]

    why.explain_removed(df, row=1)

    output = capsys.readouterr().out

    why.stop()

    assert "Why was row 1 removed?" in output
    assert "Combined filter (AND):" in output
    assert "age >= 18" in output
    assert "salary > 3000" in output
    assert "Row removed because the row did not satisfy all conditions." in output


def test_combined_or_filter_is_recorded_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "age": [17, 20, 30],
            "salary": [2000, 2500, 6000],
        }
    )

    df = df[(df["age"] < 18) | (df["salary"] > 5000)]

    events = history.get_all()

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "combined_filter"
    assert event["logic"] == "or"
    assert event["conditions"] == [
        {
            "column": "age",
            "operator": "<",
            "value": 18,
        },
        {
            "column": "salary",
            "operator": ">",
            "value": 5000,
        },
    ]
    assert event["removed_rows"] == [1]

    why.explain_removed(df, row=1)

    output = capsys.readouterr().out

    why.stop()

    assert "Why was row 1 removed?" in output
    assert "Combined filter (OR):" in output
    assert "age < 18" in output
    assert "salary > 5000" in output
    assert "Row removed because the row did not satisfy any condition." in output


def test_astype_is_recorded_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "age": [25.0, 30.0],
        }
    )

    df["age"] = df["age"].astype(int)

    events = [event for event in history.get_all() if event["type"] == "astype"]

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "astype"
    assert event["column"] == "age"
    assert event["source"] == "age"
    assert event["dtype"] == "<class 'int'>"

    why.explain(df, row=0, column="age")

    output = capsys.readouterr().out

    why.stop()

    assert "Why is age = 25?" in output
    assert "Transformation:" in output
    assert "astype(<class 'int'>)" in output
    assert "age → age" in output
    assert "age = 25" in output


def test_round_is_recorded_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "price": [12.3456, 19.999],
        }
    )

    df["price"] = df["price"].round(2)

    events = [event for event in history.get_all() if event["type"] == "round"]

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "round"
    assert event["column"] == "price"
    assert event["source"] == "price"
    assert event["decimals"] == 2

    why.explain(df, row=0, column="price")

    output = capsys.readouterr().out

    why.stop()

    assert "Why is price = 12.35?" in output
    assert "Transformation:" in output
    assert "round(2)" in output
    assert "price → price" in output
    assert "price = 12.35" in output


def test_rename_is_recorded_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "price": [100, 200],
        }
    )

    df = df.rename(columns={"price": "unit_price"})

    events = [event for event in history.get_all() if event["type"] == "rename"]

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "rename"
    assert event["columns"] == {"price": "unit_price"}

    why.explain(df, row=0, column="unit_price")

    output = capsys.readouterr().out

    why.stop()

    assert "Why is unit_price = 100?" in output
    assert "Transformation:" in output
    assert "rename()" in output
    assert "price → unit_price" in output
    assert "unit_price = 100" in output


def test_map_is_recorded_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "status": ["A", "I"],
        }
    )

    df["status"] = df["status"].map(
        {
            "A": "Active",
            "I": "Inactive",
        }
    )

    events = [event for event in history.get_all() if event["type"] == "map"]

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "map"
    assert event["column"] == "status"
    assert event["source"] == "status"
    assert event["mapping"] == {
        "A": "Active",
        "I": "Inactive",
    }

    why.explain(df, row=0, column="status")

    output = capsys.readouterr().out

    why.stop()

    assert "Why is status = Active?" in output
    assert "Transformation:" in output
    assert "map()" in output
    assert "Mapping:" in output
    assert "A → Active" in output
    assert "I → Inactive" in output
    assert "status → status" in output
    assert "status = Active" in output


def test_apply_is_recorded_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "price": [100, 200],
        }
    )

    df["double_price"] = df["price"].apply(lambda x: x * 2)

    events = [event for event in history.get_all() if event["type"] == "apply"]

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "apply"
    assert event["column"] == "double_price"
    assert event["source"] == "price"
    assert event["function"] == "<lambda>"

    why.explain(df, row=0, column="double_price")

    output = capsys.readouterr().out

    why.stop()

    assert "Why is double_price = 200?" in output
    assert "Transformation:" in output
    assert "apply(<lambda>)" in output
    assert "price → double_price" in output
    assert "double_price = 200" in output


def test_merge_is_recorded_and_explained(capsys):
    why.watch()

    customers = pd.DataFrame(
        {
            "customer_id": [1, 2],
            "name": ["Ali", "Sara"],
        }
    )

    orders = pd.DataFrame(
        {
            "customer_id": [1, 2],
            "amount": [100, 200],
        }
    )

    result = customers.merge(
        orders,
        on="customer_id",
        how="left",
    )

    events = [event for event in history.get_all() if event["type"] == "merge"]

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "merge"
    assert event["on"] == "customer_id"
    assert event["how"] == "left"

    assert event["left_dataframe_id"] == customers.attrs["_whyvalue_id"]
    assert event["right_dataframe_id"] == orders.attrs["_whyvalue_id"]
    assert event["dataframe_id"] == result.attrs["_whyvalue_id"]

    assert (
        event["left_dataframe_id"]
        != event["right_dataframe_id"]
        != event["dataframe_id"]
    )
    assert event["left_dataframe_id"] != event["dataframe_id"]

    why.explain(result, row=0, column="amount")

    output = capsys.readouterr().out

    why.stop()

    assert "Why is amount = 100?" in output
    assert "Merge:" in output
    assert "left join on customer_id" in output
    assert "This DataFrame was created by combining two data sources." in output
    assert "amount = 100" in output


def test_groupby_sum_is_recorded_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "category": ["A", "A", "B"],
            "sales": [10, 20, 30],
        }
    )

    result = df.groupby("category")["sales"].sum()

    assert result["A"] == 30
    assert result["B"] == 30

    events = [event for event in history.get_all() if event["type"] == "groupby"]

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "groupby"
    assert event["group_by"] == "category"
    assert event["source"] == "sales"
    assert event["aggregation"] == "sum"

    why.explain(result, row="A")

    output = capsys.readouterr().out

    why.stop()

    assert "Why is sales = 30?" in output
    assert "Aggregation:" in output
    assert "sum()" in output
    assert "Grouped by:" in output
    assert "category = A" in output
    assert "sales = 30" in output


def test_groupby_mean_is_recorded_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "category": ["A", "A", "B"],
            "sales": [10, 20, 30],
        }
    )

    result = df.groupby("category")["sales"].mean()

    assert result["A"] == 15
    assert result["B"] == 30

    events = [event for event in history.get_all() if event["type"] == "groupby"]

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "groupby"
    assert event["group_by"] == "category"
    assert event["source"] == "sales"
    assert event["aggregation"] == "mean"

    why.explain(result, row="A")

    output = capsys.readouterr().out

    why.stop()

    assert "Why is sales = 15.0?" in output
    assert "Aggregation:" in output
    assert "mean()" in output
    assert "Grouped by:" in output
    assert "category = A" in output
    assert "sales = 15.0" in output


def test_groupby_count_is_recorded_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "category": ["A", "A", "B"],
            "sales": [10, 20, 30],
        }
    )

    result = df.groupby("category")["sales"].count()

    assert result["A"] == 2
    assert result["B"] == 1

    events = [event for event in history.get_all() if event["type"] == "groupby"]

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "groupby"
    assert event["group_by"] == "category"
    assert event["source"] == "sales"
    assert event["aggregation"] == "count"

    why.explain(result, row="A")

    output = capsys.readouterr().out

    why.stop()

    assert "Why is sales = 2?" in output
    assert "Aggregation:" in output
    assert "count()" in output
    assert "Grouped by:" in output
    assert "category = A" in output
    assert "sales = 2" in output


def test_groupby_min_is_recorded_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "category": ["A", "A", "B"],
            "sales": [10, 20, 30],
        }
    )

    result = df.groupby("category")["sales"].min()

    assert result["A"] == 10
    assert result["B"] == 30

    events = [event for event in history.get_all() if event["type"] == "groupby"]

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "groupby"
    assert event["group_by"] == "category"
    assert event["source"] == "sales"
    assert event["aggregation"] == "min"

    why.explain(result, row="A")

    output = capsys.readouterr().out

    why.stop()

    assert "Why is sales = 10?" in output
    assert "Aggregation:" in output
    assert "min()" in output
    assert "Grouped by:" in output
    assert "category = A" in output
    assert "sales = 10" in output


def test_groupby_max_is_recorded_and_explained(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "category": ["A", "A", "B"],
            "sales": [10, 20, 30],
        }
    )

    result = df.groupby("category")["sales"].max()

    assert result["A"] == 20
    assert result["B"] == 30

    events = [event for event in history.get_all() if event["type"] == "groupby"]

    assert len(events) == 1

    event = events[0]

    assert event["type"] == "groupby"
    assert event["group_by"] == "category"
    assert event["source"] == "sales"
    assert event["aggregation"] == "max"

    why.explain(result, row="A")

    output = capsys.readouterr().out

    why.stop()

    assert "Why is sales = 20?" in output
    assert "Aggregation:" in output
    assert "max()" in output
    assert "Grouped by:" in output
    assert "category = A" in output
    assert "sales = 20" in output


def test_series_resolves_to_parent_dataframe_lineage():
    why.watch()

    df1 = pd.DataFrame({"sales": [10, 20]})
    df2 = pd.DataFrame({"sales": [100, 200]})

    s1 = df1["sales"]
    s2 = df2["sales"]

    assert df1.attrs["_whyvalue_id"] != df2.attrs["_whyvalue_id"]

    assert s1.attrs["_whyvalue_dataframe_id"] == df1.attrs["_whyvalue_id"]
    assert s2.attrs["_whyvalue_dataframe_id"] == df2.attrs["_whyvalue_id"]

    assert _get_dataframe_id(s1) == df1.attrs["_whyvalue_id"]
    assert _get_dataframe_id(s2) == df2.attrs["_whyvalue_id"]

    why.stop()


def test_untracked_object_does_not_match_unrelated_history(capsys):
    why.watch()

    tracked = pd.DataFrame({"sales": [10, 20]})
    tracked["double"] = tracked["sales"] * 2

    untracked = pd.DataFrame({"double": [999, 888]})

    events = [e for e in history.get_all() if e.get("column") == "double"]
    assert len(events) == 1
    event = events[0]

    assert _event_matches_dataframe(event, event["dataframe_id"]) is True
    assert _event_matches_dataframe(event, None) is False

    why.explain(untracked, row=0, column="double")

    output = capsys.readouterr().out

    why.stop()

    assert "No explanation found for 'double'." in output
    assert "sales" not in output


def test_dataframe_copy_gets_independent_lineage(capsys):
    why.watch()

    df1 = pd.DataFrame({"sales": [10, 20]})
    df1["a"] = 1

    df2 = df1.copy()

    assert df1.attrs["_whyvalue_id"] != df2.attrs["_whyvalue_id"]

    df2["double"] = df2["sales"] * 2

    events = [e for e in history.get_all() if e.get("column") == "double"]
    assert len(events) == 1
    event = events[0]

    assert event["dataframe_id"] == df2.attrs["_whyvalue_id"]
    assert event["dataframe_id"] != df1.attrs["_whyvalue_id"]

    assert _find_event(df1, "double") is None
    assert _find_event(df2, "double") == event

    why.explain(df1, row=0, column="double")
    df1_output = capsys.readouterr().out

    why.explain(df2, row=0, column="double")
    df2_output = capsys.readouterr().out

    why.stop()

    assert "No explanation found for 'double'." in df1_output

    assert "Why is double = 20?" in df2_output
    assert "sales = 10" in df2_output
    assert "10 × 2" in df2_output
    assert "double = 20" in df2_output


def test_filtered_dataframes_get_independent_lineage():
    why.watch()

    df = pd.DataFrame(
        {
            "age": [17, 20, 30],
            "sales": [100, 200, 300],
        }
    )

    a = df[df["age"] >= 18]
    b = df[df["age"] < 18]

    assert "_whyvalue_id" in df.attrs
    assert "_whyvalue_id" in a.attrs
    assert "_whyvalue_id" in b.attrs

    assert a.attrs["_whyvalue_id"] != b.attrs["_whyvalue_id"]
    assert a.attrs["_whyvalue_id"] != df.attrs["_whyvalue_id"]
    assert b.attrs["_whyvalue_id"] != df.attrs["_whyvalue_id"]

    events = [e for e in history.get_all() if e.get("type") == "filter"]
    assert len(events) == 2

    event_a = next(e for e in events if e["dataframe_id"] == a.attrs["_whyvalue_id"])
    event_b = next(e for e in events if e["dataframe_id"] == b.attrs["_whyvalue_id"])

    assert event_a["source_dataframe_id"] == df.attrs["_whyvalue_id"]
    assert event_b["source_dataframe_id"] == df.attrs["_whyvalue_id"]

    b["bonus"] = b["sales"] * 2

    assert _find_event(a, "bonus") is None

    b_bonus_event = _find_event(b, "bonus")
    assert b_bonus_event is not None
    assert b_bonus_event["dataframe_id"] == b.attrs["_whyvalue_id"]

    why.stop()


def test_filter_preserves_source_history_for_explain_removed(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "name": ["Ali", "Ahmed", "Sara"],
            "age": [25, None, 17],
        }
    )

    df["age"] = df["age"].fillna(0)

    filtered = df[df["age"] >= 18]

    why.explain_removed(filtered, row=1)

    output = capsys.readouterr().out

    why.stop()

    assert "Why was row 1 removed?" in output
    assert "Original age:" in output
    assert "NaN" in output
    assert "fillna(0)" in output
    assert "NaN → 0.0" in output
    assert "Filter:" in output
    assert "age >= 18" in output
    assert "0.0 >= 18 → False" in output
    assert "Row removed" in output


def test_dropna_results_get_independent_lineage(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "age": [20, None, 30],
            "sales": [100, 200, None],
        }
    )

    a = df.dropna(subset=["age"])
    b = df.dropna(subset=["sales"])

    assert df.attrs["_whyvalue_id"] != a.attrs["_whyvalue_id"]
    assert df.attrs["_whyvalue_id"] != b.attrs["_whyvalue_id"]
    assert a.attrs["_whyvalue_id"] != b.attrs["_whyvalue_id"]

    events = [e for e in history.get_all() if e.get("type") == "dropna"]
    assert len(events) == 2

    event_a = next(e for e in events if e["dataframe_id"] == a.attrs["_whyvalue_id"])
    event_b = next(e for e in events if e["dataframe_id"] == b.attrs["_whyvalue_id"])

    assert event_a["dataframe_id"] == a.attrs["_whyvalue_id"]
    assert event_a["source_dataframe_id"] == df.attrs["_whyvalue_id"]

    assert event_b["dataframe_id"] == b.attrs["_whyvalue_id"]
    assert event_b["source_dataframe_id"] == df.attrs["_whyvalue_id"]

    b["bonus"] = b["sales"] * 2

    assert _find_event(a, "bonus") is None

    b_bonus_event = _find_event(b, "bonus")
    assert b_bonus_event is not None
    assert b_bonus_event["dataframe_id"] == b.attrs["_whyvalue_id"]

    why.explain_removed(a, row=1)

    output = capsys.readouterr().out

    assert "Why was row 1 removed?" in output
    assert "dropna(subset=['age'])" in output
    assert "Row removed because required data was missing." in output

    df_inplace = pd.DataFrame(
        {
            "age": [20, None, 30],
            "sales": [100, 200, None],
        }
    )

    id_before = _get_adapter_dataframe_id(df_inplace)

    df_inplace.dropna(subset=["age"], inplace=True)

    assert df_inplace.attrs["_whyvalue_id"] == id_before

    why.stop()


def test_rename_results_get_independent_lineage(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "price": [10, 20],
        }
    )

    a = df.rename(columns={"price": "unit_price"})
    b = df.rename(columns={"price": "cost"})

    assert df.attrs["_whyvalue_id"] != a.attrs["_whyvalue_id"]
    assert df.attrs["_whyvalue_id"] != b.attrs["_whyvalue_id"]
    assert a.attrs["_whyvalue_id"] != b.attrs["_whyvalue_id"]

    events = [e for e in history.get_all() if e.get("type") == "rename"]
    assert len(events) == 2

    event_a = next(e for e in events if e["dataframe_id"] == a.attrs["_whyvalue_id"])
    event_b = next(e for e in events if e["dataframe_id"] == b.attrs["_whyvalue_id"])

    assert event_a["dataframe_id"] == a.attrs["_whyvalue_id"]
    assert event_a["source_dataframe_id"] == df.attrs["_whyvalue_id"]

    assert event_b["dataframe_id"] == b.attrs["_whyvalue_id"]
    assert event_b["source_dataframe_id"] == df.attrs["_whyvalue_id"]

    b["double_cost"] = b["cost"] * 2

    assert _find_event(a, "double_cost") is None

    b_double_cost_event = _find_event(b, "double_cost")
    assert b_double_cost_event is not None
    assert b_double_cost_event["dataframe_id"] == b.attrs["_whyvalue_id"]

    why.explain(a, row=0, column="unit_price")

    output = capsys.readouterr().out

    assert "Why is unit_price = 10?" in output
    assert "Transformation:" in output
    assert "rename()" in output
    assert "price → unit_price" in output
    assert "unit_price = 10" in output

    df_inplace = pd.DataFrame(
        {
            "price": [10, 20],
        }
    )

    id_before = _get_adapter_dataframe_id(df_inplace)

    df_inplace.rename(
        columns={"price": "unit_price"},
        inplace=True,
    )

    assert df_inplace.attrs["_whyvalue_id"] == id_before

    why.stop()


def test_cross_dataframe_direct_assignment_tracks_source_lineage(capsys):
    why.watch()

    df1 = pd.DataFrame(
        {
            "id": [1, 2],
        }
    )

    df2 = pd.DataFrame(
        {
            "sales": [100, 200],
        }
    )

    df1_id = _get_adapter_dataframe_id(df1)
    df2_id = _get_adapter_dataframe_id(df2)

    df1["copied"] = df2["sales"]

    events = [e for e in history.get_all() if e.get("column") == "copied"]
    assert len(events) == 1
    event = events[0]

    assert event["type"] == "column_created"
    assert event["dataframe_id"] == df1_id
    assert event["column"] == "copied"
    assert event["operation"] == "copy"
    assert event["source"] == "sales"
    assert event["source_dataframe_id"] == df2_id

    why.explain(df1, row=0, column="copied")

    output = capsys.readouterr().out

    assert "Why is copied = 100?" in output
    assert "Copied from column:" in output
    assert "sales" in output
    assert "Source: another DataFrame" in output
    assert "copied = 100" in output

    why.stop()


def test_cross_dataframe_arithmetic_tracks_operand_lineage(capsys):
    why.watch()

    df1 = pd.DataFrame(
        {
            "a": [10, 20],
        }
    )

    df2 = pd.DataFrame(
        {
            "b": [1, 2],
        }
    )

    df1_id = _get_adapter_dataframe_id(df1)
    df2_id = _get_adapter_dataframe_id(df2)

    df1["result"] = df1["a"] + df2["b"]

    events = [e for e in history.get_all() if e.get("column") == "result"]
    assert len(events) == 1
    event = events[0]

    assert event["type"] == "column_created"
    assert event["dataframe_id"] == df1_id
    assert event["column"] == "result"
    assert event["operation"] == "add"

    assert event["left"] == "a"
    assert event["right"] == "b"
    assert event["right_type"] == "column"

    assert event["left_dataframe_id"] == df1_id
    assert event["right_dataframe_id"] == df2_id

    why.explain(df1, row=0, column="result")

    output = capsys.readouterr().out

    assert "Why is result = 11?" in output
    assert "a = 10" in output
    assert "b came from another DataFrame." in output
    assert "Operation:" in output
    assert "a + b" in output
    assert "→ result = 11" in output

    df_same = pd.DataFrame(
        {
            "a": [10, 20],
            "b": [1, 2],
        }
    )

    df_same["result"] = df_same["a"] + df_same["b"]

    why.explain(df_same, row=0, column="result")

    output_same = capsys.readouterr().out

    assert "a = 10" in output_same
    assert "b = 1" in output_same
    assert "10 + 1" in output_same
    assert "→ result = 11" in output_same

    why.stop()


def test_sequential_same_column_transformations_show_history(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "value": [1.234, None],
        }
    )

    df["value"] = df["value"].fillna(0)
    df["value"] = df["value"].astype(float)
    df["value"] = df["value"].round(1)

    events = _find_events(df, "value")
    assert len(events) == 3
    assert events[0]["type"] == "column_filled"
    assert events[1]["type"] == "astype"
    assert events[2]["type"] == "round"

    why.explain(df, row=1, column="value")

    output = capsys.readouterr().out

    assert "Why is value = 0.0?" in output
    assert "Transformation history:" in output
    assert "1. fillna(0)" in output
    assert "2. astype(<class 'float'>)" in output
    assert "3. round(1)" in output
    assert "Final:" in output
    assert "value = 0.0" in output

    fillna_pos = output.find("fillna(0)")
    astype_pos = output.find("astype")
    round_pos = output.find("round(1)")

    assert fillna_pos < astype_pos < round_pos

    why.stop()


def test_derived_column_then_transform_shows_full_history(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "price": [10, 20],
        }
    )

    df["double"] = df["price"] * 2
    df["double"] = df["double"].round(0)

    why.explain(df, row=0, column="double")

    output = capsys.readouterr().out

    assert "Why is double = 20?" in output
    assert "Transformation history:" in output
    assert "1. price × 2 → double" in output
    assert "2. round(0)" in output
    assert "Final:" in output
    assert "double = 20" in output

    arith_pos = output.find("price × 2 → double")
    round_pos = output.find("round(0)")

    assert arith_pos < round_pos

    single = pd.DataFrame({"price": [10, 20]})
    single["double"] = single["price"] * 2

    why.explain(single, row=0, column="double")

    single_output = capsys.readouterr().out

    assert "price = 10" in single_output
    assert "10 × 2" in single_output
    assert "→ double = 20" in single_output
    assert "Transformation history:" not in single_output

    why.stop()


def test_groupby_explain_includes_source_transformation_history(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "category": ["A", "A", "B"],
            "sales": [10.4, 20.6, 30.2],
        }
    )

    df["sales"] = df["sales"].round(0)

    result = df.groupby("category")["sales"].sum()

    why.explain(result, row="A")

    output = capsys.readouterr().out

    assert "Why is sales = 31.0?" in output
    assert "Source transformation history:" in output
    assert "1. round(0)" in output
    assert "Aggregation:" in output
    assert "sum()" in output
    assert "Grouped by:" in output
    assert "category = A" in output
    assert "Final:" in output
    assert "sales = 31.0" in output

    round_pos = output.find("1. round(0)")
    agg_pos = output.find("Aggregation:")
    final_pos = output.find("Final:")

    assert round_pos < agg_pos < final_pos

    why.stop()


def test_groupby_explain_includes_multi_step_source_history(capsys):
    why.watch()

    df = pd.DataFrame(
        {
            "category": ["A", "A", "B"],
            "sales": [10.44, None, 30.22],
        }
    )

    df["sales"] = df["sales"].fillna(0)
    df["sales"] = df["sales"].astype(float)
    df["sales"] = df["sales"].round(1)

    result = df.groupby("category")["sales"].sum()

    why.explain(result, row="A")

    output = capsys.readouterr().out

    assert "Why is sales = 10.4?" in output
    assert "Source transformation history:" in output
    assert "1. fillna(0)" in output
    assert "2. astype(<class 'float'>)" in output
    assert "3. round(1)" in output
    assert "Aggregation:" in output
    assert "sum()" in output
    assert "Grouped by:" in output
    assert "category = A" in output
    assert "Final:" in output
    assert "sales = 10.4" in output

    fillna_pos = output.find("fillna(0)")
    astype_pos = output.find("astype")
    round_pos = output.find("round(1)")
    agg_pos = output.find("Aggregation:")

    assert fillna_pos < astype_pos < round_pos < agg_pos

    plain = pd.DataFrame(
        {
            "category": ["A", "A"],
            "sales": [10, 20],
        }
    )

    plain_result = plain.groupby("category")["sales"].sum()

    why.explain(plain_result, row="A")

    plain_output = capsys.readouterr().out

    assert "Source transformation history:" not in plain_output
    assert "Aggregation:" in plain_output
    assert "sum()" in plain_output
    assert "Grouped by:" in plain_output
    assert "category = A" in plain_output
    assert "sales = 30" in plain_output

    why.stop()
