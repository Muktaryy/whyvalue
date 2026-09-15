![WhyValue](docs/assets/branding.png)

# WhyValue

> Ask your data why.

WhyValue is a developer-first Python library for tracking data transformations and explaining why values have the values they do.

WhyValue captures end-to-end data provenance across:

- Python lists and dictionaries (`TrackedList`, `TrackedDict`)
- JSON files
- CSV files
- TXT files
- HTTP APIs
- pandas DataFrames & Series

---

## The Core Idea

```text
SOURCE
  ↓
TRANSFORMATION
  ↓
VALUE
  ↓
EXPLANATION
```

When working with data pipelines, it is easy to see *what* final value a variable holds, but much harder to answer *why* it has that value.

- `why.trace(obj)` tells you **what** happened.
- `why.explain(obj, ...)` tells you **why** a specific value exists.

---

## Installation

```bash
pip install whyvalue
```

For local or development installation from source:

```bash
pip install -e .
```

*Note: WhyValue v0.2 development is complete and preparing for its formal v0.2.0 PyPI release.*

---

## Quick Start

Track native Python dictionaries and lists:

```python
import whyvalue as why

with why.watch():
    user = why.track({
        "name": "Ali",
        "age": 21
    })

    user["age"] = 22

    why.explain(user, key="age")
```

**Output:**

```text
Why is age = 22?

Source:
Memory object

Format:
Python object

Transformation history:

1. Created dict {'name': 'Ali', 'age': 21}
2. set age = 22

Final:
age = 22
```

---

## Cross-Source Lineage Example

Load data from a CSV file, convert it to a pandas DataFrame via `why.to_dataframe()`, transform the columns, and explain the calculated result:

```python
import whyvalue as why

with why.watch():
    rows = why.load_csv("sales.csv")
    df = why.to_dataframe(rows)

    df["price"] = df["price"].astype(float)
    df["quantity"] = df["quantity"].astype(int)
    df["total"] = df["price"] * df["quantity"]

    why.explain(df, row=0, column="total")
```

```text
CSV
 ↓
Tracked data
 ↓
DataFrame
 ↓
transformations
 ↓
final value
 ↓
explanation
```

WhyValue traces the final `total` cell all the way back to the original CSV file line and column name.

---

## Supported Features

| Category | Supported Capabilities |
| :--- | :--- |
| **Python** | `TrackedList`, `TrackedDict` |
| **Data Sources** | JSON (`why.load_json`), CSV (`why.load_csv`), TXT (`why.load_txt`), HTTP GET APIs (`why.get`) |
| **Pandas Operations** | Arithmetic (`+`, `-`, `*`, `/`), filtering (`>`, `>=`, `<`, `<=`, `==`, `!=`, `&`, `\|`), `fillna()`, `dropna(subset=[...])`, column operations (`astype`, `round`, `rename`, `map`, `apply`), DataFrame merges (`merge`), SeriesGroupBy aggregations (`sum`, `mean`, `count`, `min`, `max`) |
| **Provenance & Inspection** | `why.trace()`, `why.explain()`, `why.explain_removed()`, explanation modes (`full`, `short`, `json`), optional state snapshots (`snapshot=True`), cross-source bridge (`why.to_dataframe()`) |

---

## Data Sources

WhyValue attaches structured origin metadata as data enters your Python session:

- **JSON**: `file → JSON path → value` (e.g. `$.users[0].name`)
- **CSV**: `file → row → column → value` (1-based data-row index mapping)
- **TXT**: `file → line → value` (1-based line number tracking)
- **HTTP**: `request → JSON path → value` (sanitized URL, status code, method)
- **Python**: `tracked object → mutation → value` (`TrackedList`, `TrackedDict`)

---

## Snapshots

When state snapshots are enabled during a watch session:

```python
with why.watch(snapshot=True):
    df["val"] = df["val"].fillna(0)
```

WhyValue captures before-and-after states for supported operations (such as `fillna`), allowing `why.explain()` to report exact previous values prior to transformation at the cost of additional memory.

---

## Documentation

Full documentation, tutorials, and topic guides are available in the project documentation directory:

[Read the documentation](docs/index.html)

---

## Project Status

WhyValue v0.2 development is complete and preparing for release.

Current test suite: **174 tests passing**.

WhyValue is still an early-stage project.

---

## Limitations

- **Active tracking required:** Operations are recorded only while an active `why.watch()` session is running.
- **In-memory history:** Event history is stored in memory and resets whenever a new `why.watch()` session starts.
- **Pandas scope:** Operations cover selected pandas methods, arithmetic operators, filters, missing data handlers, and aggregations (not the entire pandas API).
- **Cross-source requirement:** Cross-source pandas lineage requires bridging tracked inputs with `why.to_dataframe()`.
- **Memory impact:** Enabling `snapshot=True` increases memory consumption by storing copy snapshots of transformed data.
- **CSV string types:** Data loaded via `why.load_csv()` initially contains string values until explicitly coerced or transformed.
- **HTTP helper scope:** HTTP tracking currently uses the explicit `why.get()` helper rather than globally intercepting all `requests` module calls.
- **Unintegrated engines:** NumPy, Polars, SQL databases, and DuckDB are not yet supported.

---

## Roadmap

Future directions under consideration:

- NumPy array integration
- Polars DataFrame integration
- SQL and database query lineage
- DuckDB engine support
- Richer graph visualization for provenance chains
- Broader pandas operation coverage

---

## Development

Run the test suite locally:

```bash
python -m pytest
```

*(Current audited checkpoint: 174 passing tests.)*

Build distribution packages:

```bash
python -m build
```

---

## Links

- **GitHub Repository**: [https://github.com/Muktaryy/whyvalue](https://github.com/Muktaryy/whyvalue)
- **PyPI Package**: [https://pypi.org/project/whyvalue/](https://pypi.org/project/whyvalue/)
