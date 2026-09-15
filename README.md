<p align="center">
  <a href="https://muktaryy.github.io/whyvalue/">
    <img src="https://raw.githubusercontent.com/Muktaryy/whyvalue/main/docs/assets/whyvalue-readme.png" alt="WhyValue Logo" width="400" />
  </a>
</p>

<h3 align="center">Ask Your Data Why</h3>

<p align="center">
  <em>Transparent data lineage and value provenance for Python.</em>
</p>

<p align="center">
  <a href="https://pypi.org/project/whyvalue/"><img src="https://img.shields.io/pypi/v/whyvalue.svg" alt="PyPI Version"></a>
  <a href="https://pypi.org/project/whyvalue/"><img src="https://img.shields.io/pypi/pyversions/whyvalue.svg" alt="Python Versions"></a>
  <a href="https://github.com/Muktaryy/whyvalue/blob/main/LICENSE"><img src="https://img.shields.io/github/license/Muktaryy/whyvalue.svg" alt="License"></a>
  <a href="https://muktaryy.github.io/whyvalue/"><img src="https://img.shields.io/badge/docs-live-blue.svg" alt="Documentation"></a>
</p>

---

## What is WhyValue?

**WhyValue** is a developer-first Python library for data lineage, mutation tracking, and value provenance.

When a pipeline yields an unexpected calculation, a missing field, or an invalid metric, traditional debugging requires stepping through code line-by-line or placing manual print statements across modules. **WhyValue** eliminates this guesswork by capturing the history of your data as it flows from file and network sources through Python objects and pandas DataFrames.

Whenever you ask **"Why does this variable have this value?"**, WhyValue delivers a human-readable explanation of its origin, file boundaries, mathematical operations, and mutation sequence.

---

## Core Mental Model

WhyValue operates as a runtime observer:

```
┌─────────────────┐       ┌──────────────────────┐       ┌─────────────────┐       ┌──────────────────────┐
│   Source Data   │ ────► │    Transformations   │ ────► │   Target Value  │ ────► │   Lineage & Provenance│
│ CSV, JSON, HTTP │       │ Math, Mutates, pandas│       │ Dict, DF, List  │       │ why.explain(target)  │
└─────────────────┘       └──────────────────────┘       └─────────────────┘       └──────────────────────┘
```

1. **Watch**: Wrap execution blocks with `with why.watch():` to activate observation.
2. **Track**: Ingest file/HTTP sources (`why.load_csv`, `why.get`) or wrap native structures (`why.track()`).
3. **Explain**: Query any value or cell at any point using `why.explain()` to inspect its transformation sequence.

---

## Key Features

- 🔍 **Non-Invasive Tracing**: Transparently observes object mutations without altering standard Python semantics.
- 🌐 **Cross-Source Lineage**: Tracks data across CSV files, JSON documents, text files, and HTTP API responses.
- 🐼 **Pandas Integration**: Observes DataFrame column creation, element-wise arithmetic, filtering, and assignment.
- 📜 **Transformation History**: Explains origins down to file names, source line/row indices, and math formulas.
- 📸 **Snapshot Auditing**: Optional before-and-after state capturing for auditing using `why.watch(snapshot=True)`.
- ⚡ **Lightweight & Fast**: Pure Python core with minimal dependency requirements for native tracking.

---

## Installation

Install WhyValue via PyPI using `pip`:

```bash
pip install whyvalue
```

*Requirements: Python 3.10+*

---

## Quick Start

### 1. Tracking Native Python Objects

Track mutations on standard dictionaries and lists:

```python
import whyvalue as why

with why.watch():
    user = why.track({"name": "Ali", "age": 21})
    user["age"] = 22
    user["status"] = "active"

    # Ask WhyValue why user['age'] equals 22
    why.explain(user, key="age")
```

**Output:**

```text
Why is age = 22?

Transformation history:

1. Original: age = 21
2. set age = 22

Final:
age = 22
```

---

### 2. Cross-Source Lineage: CSV to Pandas

Track data as it flows from external files into pandas DataFrames and derived columns:

```python
import pandas as pd
import whyvalue as why

with why.watch():
    # Load and track raw CSV data
    rows = why.load_csv("sales.csv")

    # Convert tracked rows into a tracked DataFrame
    df = why.to_dataframe(rows)

    # Perform pandas calculations
    df["total"] = df["price"].astype(float) * df["quantity"].astype(int)

    # Explain the lineage of a calculated cell
    why.explain(df, row=0, column="total")
```

**Output:**

```text
Why is total = 59.97?

Source:
sales.csv

Format:
CSV

Source row:
1

Transformations:

1. price × quantity → total

Final:
total = 59.97
```

---

## Feature Matrix

| Feature / Domain | Supported Operations | Description |
| :--- | :--- | :--- |
| **Native Python** | `dict`, `list`, primitive scalars | Tracks key assignments, item appends, deletions, and updates. |
| **File I/O** | `why.load_csv()`, `why.load_json()`, `why.load_txt()` | Ingests files while binding line/row indices for origin tracking. |
| **HTTP Requests** | `why.get(url)` | Records API URLs, HTTP response metadata, and payload structures. |
| **Pandas DataFrames**| `why.to_dataframe()`, column math, assignments | Tracks column derivations (`df['a'] * df['b']`), fills, and splits. |
| **Lineage & Inspection** | `why.explain()`, `why.explain_removed()`, `why.trace()` | Generates step-by-step human-readable transformation histories. |
| **State Snapshots** | `why.watch(snapshot=True)` | Captures state copies before and after operations for auditing. |

---

## Main API Overview

| Function | Signature | Description |
| :--- | :--- | :--- |
| `why.watch()` | `watch(snapshot=False)` | Context manager to begin observing data operations. |
| `why.track()` | `track(obj)` | Wraps a native `dict` or `list` for mutation tracking. |
| `why.explain()` | `explain(target, key=None, row=None, column=None)` | Prints the lineage and transformation history of a value. |
| `why.explain_removed()` | `explain_removed(target, key=None)` | Explains why a key or item was removed from a collection. |
| `why.trace()` | `trace(df)` | Prints a summary of all column transformations on a DataFrame. |
| `why.load_csv()` | `load_csv(path_or_str)` | Loads a CSV file into tracked dictionary records. |
| `why.load_json()` | `load_json(path_or_str)` | Loads a JSON document into tracked nested structures. |
| `why.load_txt()` | `load_txt(path_or_str)` | Loads a text file into tracked line lists. |
| `why.get()` | `get(url, **kwargs)` | Fetches HTTP API endpoints and tracks JSON response bodies. |
| `why.to_dataframe()` | `to_dataframe(tracked_data)` | Converts tracked records into a lineage-aware pandas DataFrame. |

---

## Performance & Best Practices

WhyValue is engineered for development, data pipeline auditing, debugging, and automated tests.

- **No Overhead when Inactive**: Calling code outside of `with why.watch():` incurs no tracking overhead.
- **In-Memory Tracking**: Event history is maintained in memory during a watch session and released upon completion.
- **Snapshot Mode**: Use `snapshot=True` only when full state auditing is required for complex transformations.

---

## What's New in v0.2

- 🚀 **Cross-Source Tracking**: Provenance across CSV, JSON, TXT files, and HTTP APIs.
- 🐼 **Full Pandas Integration**: Column math, element-wise transformations, and DataFrame lineage.
- 📊 **Enhanced Explanations**: Improved transformation outputs with file names, line numbers, and math symbols.
- ⚡ **Streamlined API**: Dedicated file loaders (`load_csv`, `load_json`, `load_txt`) and HTTP wrappers.

---

## Documentation & Resources

- 📖 **Live Documentation Website**: [https://muktaryy.github.io/whyvalue/](https://muktaryy.github.io/whyvalue/)
- 📦 **PyPI Package**: [https://pypi.org/project/whyvalue/](https://pypi.org/project/whyvalue/)
- 💻 **GitHub Repository**: [https://github.com/Muktaryy/whyvalue](https://github.com/Muktaryy/whyvalue)
- 🐛 **Issue Tracker**: [https://github.com/Muktaryy/whyvalue/issues](https://github.com/Muktaryy/whyvalue/issues)

---

## License

WhyValue is released under the [MIT License](LICENSE).

Developed and maintained by **Muktar Yakub**.
