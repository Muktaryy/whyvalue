# WhyValue

> Ask your data why.

WhyValue is a lightweight developer tool for pandas that tracks data transformations and answers questions about how values in your DataFrames were created, modified, filtered, filled, aggregated, or removed.

When working with complex pandas pipelines, it is easy to see *what* final value a cell holds, but much harder to answer *why* it has that value. WhyValue records transformation history while `why.watch()` is active so you can inspect line-by-line provenance using `why.explain()`, `why.trace()`, and `why.explain_removed()`.

---

## 1. Why WhyValue?

A typical pandas pipeline might end with:

```python
price = 20
```

When an output looks unexpected, the critical question is:

> **Why is `price` 20?**

Without tracking, finding the answer requires manually stepping through notebook cells or script transformations. WhyValue records execution history as operations occur and builds structured, human-readable explanations on demand.

---

## 2. Installation

Intended release installation:

```bash
pip install whyvalue
```

For local or development installation from source:

```bash
pip install -e .
```

---

## 3. Quick Start

```python
import pandas as pd
import whyvalue as why

# Start tracking pandas operations
why.watch()

df = pd.DataFrame(
    {
        "price": [10, 20],
        "quantity": [2, 3],
    }
)

df["total"] = df["price"] * df["quantity"]

# Explain how total was computed for row 0
why.explain(df, row=0, column="total")

# Stop tracking and restore original pandas methods
why.stop()
```

**Output:**

```text
Why is total = 20?

price = 10
quantity = 2

10 × 2
→ total = 20
```

---

## 4. Core API

### `why.watch()`
Starts tracking supported pandas operations. Calling `why.watch()` multiple times is safe (subsequent calls are safe no-ops). Starting a new `why.watch()` session clears any previously recorded in-memory history.

### `why.stop()`
Stops tracking and restores original pandas methods. Calling `why.stop()` does not immediately erase recorded history, so previous history remains available until the next `why.watch()` session resets it.

### `why.is_watching()`
Returns `True` if WhyValue is currently actively tracking operations, and `False` otherwise.

### `why.trace(obj)`
Prints a high-level summary of recorded transformations for the given DataFrame.

### `why.explain(obj, row, column=None)`
Explains how a specific cell value was calculated or transformed, including arithmetic operands, applied functions, and sequential transformation steps.

### `why.explain_removed(obj=None, row=None)`
Explains why a specific row index was removed by a filter or `dropna()` operation.

---

## 5. Sequential Transformation History

When a column undergoes multiple sequential transformations, WhyValue records the full operation history:

```python
import pandas as pd
import whyvalue as why

why.watch()

df = pd.DataFrame({"value": [1.234, None]})

df["value"] = df["value"].fillna(0)
df["value"] = df["value"].astype(float)
df["value"] = df["value"].round(1)

why.explain(df, row=1, column="value")

why.stop()
```

**Output:**

```text
Why is value = 0.0?

Transformation history:

1. fillna(0)
2. astype(<class 'float'>)
3. round(1)

Final:
value = 0.0
```

*Note: WhyValue records the sequence of operations applied to a column. It does not snapshot intermediate cell-value states between operations.*

---

## 6. GroupBy Source History

WhyValue tracks column history across supported GroupBy aggregations:

```python
import pandas as pd
import whyvalue as why

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

why.stop()
```

**Output:**

```text
Why is sales = 31.0?

Source transformation history:

1. round(0)

Aggregation:
sum()

Grouped by:
category = A

Final:
sales = 31.0
```

**Supported GroupBy Aggregations in v0.1:**
- `sum()`
- `mean()`
- `count()`
- `min()`
- `max()`

---

## 7. Supported Pandas Features

| Category | Supported Operations |
| :--- | :--- |
| **Arithmetic** | Column-column (`+`, `-`, `*`, `/`), column-scalar, scalar-column, reverse arithmetic |
| **Filtering** | Comparison operators (`>`, `>=`, `<`, `<=`, `==`, `!=`), combined AND (`&`), combined OR (`\|`) |
| **Missing Data** | `fillna()`, `dropna(subset=[...])` |
| **Column Operations** | `astype()`, `round()`, `map()` (dict mappings), `apply()` (func label) |
| **DataFrame Operations**| `rename()`, `copy()` lineage isolation |
| **Merges** | `DataFrame.merge()` (`on=`, common `how=` joins) |
| **GroupBy** | `groupby()[col].sum()`, `mean()`, `count()`, `min()`, `max()` |

---

## 8. Example: Removed Row Explanation

```python
import pandas as pd
import whyvalue as why

why.watch()

df = pd.DataFrame(
    {
        "name": ["Ali", "Ahmed", "Sara"],
        "age": [25, None, 17],
    }
)

df = df.dropna(subset=["age"])

why.explain_removed(df, row=1)

why.stop()
```

**Output:**

```text
Why was row 1 removed?

dropna(subset=['age'])

Row removed because required data was missing.
```

---

## 9. How It Works

While `why.watch()` is active, WhyValue hooks selected pandas methods and operators. Each operation generates a lightweight in-memory event linked to unique DataFrame lineage IDs.

When you call `why.explain()`, WhyValue inspects the recorded lineage graph and events for that DataFrame and column to reconstruct a human-readable explanation.

WhyValue acts as an inspection layer on top of pandas; it does not replace or re-implement pandas data structures.

---

## 10. v0.1 Limitations

- **Pandas only:** Supported exclusively for pandas DataFrames and Series in v0.1.
- **Active tracking required:** Operations are recorded only while `why.watch()` is active.
- **In-memory history:** Event history is stored in memory and resets whenever `why.watch()` is called.
- **No value snapshots:** WhyValue records operation history and parameters, but does not snapshot intermediate cell values between transformations.
- **Merge provenance scope:** Merges record parent DataFrame IDs, join keys, and join types, but do not yet trace individual output column origins for overlapping/suffixed columns.
- **GroupBy scope:** GroupBy aggregations are limited to `sum`, `mean`, `count`, `min`, and `max`.
- **Method limitations:** `map()` provenance focuses on dictionary mappings; `apply()` records function name labels rather than analyzing function bodies.
- **No external integrations yet:** NumPy, Requests/HTTP API, and SQL database lineage are not supported in v0.1.

---

## 11. Roadmap

### v0.1 (Current)
- Pandas operation explanations
- Filter and removal tracing
- Missing data tracking (`fillna`, `dropna`)
- DataFrame copy & lineage isolation
- Basic merge & GroupBy aggregation support
- Sequential column transformation history

### Future
- Column-origin provenance for complex merges
- NumPy array integration
- HTTP API / Requests data source tracking
- SQL database lineage
- Richer provenance graph visualization
- Optional intermediate value snapshotting

---

## 12. Development

To run the test suite locally:

```bash
python -m pytest
```

*(At the v0.1 release checkpoint, the test suite contains 49 passing tests.)*

To build source distribution and wheel packages:

```bash
python -m build
```

---

## 13. Status

**WhyValue v0.1.0** is an early-stage, experimental developer tool.

