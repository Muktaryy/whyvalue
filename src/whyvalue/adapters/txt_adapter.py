import copy
from pathlib import Path

from .python_list import TrackedList
from ..history import history
from ..provenance import ProvenanceEvent


def load_txt(path, encoding="utf-8", keepends=False):
    """Load text from a file path into a WhyValue TrackedList of strings."""
    from ..core import is_watching, is_snapshot_enabled

    if not is_watching():
        raise RuntimeError("why.load_txt() requires an active WhyValue watch session.")

    file_path = Path(path)

    # Let native FileNotFoundError, UnicodeDecodeError etc. propagate natively
    with open(file_path, mode="r", encoding=encoding) as f:
        content = f.read()

    lines = content.splitlines(keepends=keepends)
    is_snapshot = is_snapshot_enabled()

    lines_list = TrackedList()
    lines_list._whyvalue_source = {
        "source_type": "txt",
        "source_format": "TXT",
        "source_path": str(path),
        "encoding": encoding,
        "keepends": keepends,
        "line_count": len(lines),
    }

    for line in lines:
        super(TrackedList, lines_list).append(line)

    history.add(
        ProvenanceEvent(
            event_type="txt_loaded",
            object_id=lines_list._whyvalue_id,
            after_value=copy.deepcopy(list(lines_list)) if is_snapshot else None,
            inputs={
                "source_path": str(path),
                "line_count": len(lines),
                "initial_value": copy.deepcopy(list(lines_list)),
            },
            metadata={
                "operation": "txt_loaded",
                "source_type": "txt",
                "source_path": str(path),
                "encoding": encoding,
                "keepends": keepends,
                "line_count": len(lines),
                "initial_value": copy.deepcopy(list(lines_list)),
            },
        )
    )

    return lines_list
