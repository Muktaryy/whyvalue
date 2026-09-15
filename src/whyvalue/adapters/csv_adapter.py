import copy
import csv
from pathlib import Path

from .python_dict import TrackedDict
from .python_list import TrackedList
from ..history import history
from ..provenance import ProvenanceEvent


def load_csv(path, encoding="utf-8", delimiter=","):
    """Load CSV from a file path into WhyValue tracked containers (TrackedList of TrackedDict)."""
    from ..core import is_watching, is_snapshot_enabled

    if not is_watching():
        raise RuntimeError("why.load_csv() requires an active WhyValue watch session.")

    file_path = Path(path)
    is_snapshot = is_snapshot_enabled()

    with open(file_path, mode="r", encoding=encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=delimiter)

        rows_list = TrackedList()
        rows_list._whyvalue_source = {
            "source_type": "csv",
            "source_path": str(path),
            "delimiter": delimiter,
            "encoding": encoding,
        }

        row_idx = 1
        for row in reader:
            row_dict = TrackedDict()
            row_dict._whyvalue_source = {
                "source_type": "csv",
                "source_path": str(path),
                "csv_row": row_idx,
                "delimiter": delimiter,
                "encoding": encoding,
            }

            for k, v in row.items():
                super(TrackedDict, row_dict).__setitem__(k, v)

            history.add(
                ProvenanceEvent(
                    event_type="csv_loaded",
                    object_id=row_dict._whyvalue_id,
                    after_value=copy.deepcopy(dict(row_dict)) if is_snapshot else None,
                    inputs={
                        "source_path": str(path),
                        "csv_row": row_idx,
                        "initial_value": copy.deepcopy(dict(row_dict)),
                    },
                    metadata={
                        "operation": "csv_loaded",
                        "source_type": "csv",
                        "source_path": str(path),
                        "csv_row": row_idx,
                        "delimiter": delimiter,
                        "encoding": encoding,
                        "initial_value": copy.deepcopy(dict(row_dict)),
                    },
                )
            )

            super(TrackedList, rows_list).append(row_dict)
            row_idx += 1

        history.add(
            ProvenanceEvent(
                event_type="csv_loaded",
                object_id=rows_list._whyvalue_id,
                after_value=copy.deepcopy(list(rows_list)) if is_snapshot else None,
                inputs={
                    "source_path": str(path),
                    "total_rows": row_idx - 1,
                    "initial_value": copy.deepcopy(list(rows_list)),
                },
                metadata={
                    "operation": "csv_loaded",
                    "source_type": "csv",
                    "source_path": str(path),
                    "total_rows": row_idx - 1,
                    "delimiter": delimiter,
                    "encoding": encoding,
                    "initial_value": copy.deepcopy(list(rows_list)),
                },
            )
        )

        return rows_list
