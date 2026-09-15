from whyvalue.history import history
from whyvalue.provenance import ProvenanceEvent


def test_provenance_event_structured_creation():
    event = ProvenanceEvent(
        event_type="column_created",
        object_id="df_001",
        source_id="df_000",
        inputs={"left": "price", "right": "qty"},
        output="total",
        before_value=None,
        after_value=20,
        metadata={"operation": "multiply"},
    )

    assert event.event_type == "column_created"
    assert event.object_id == "df_001"
    assert event.source_id == "df_000"
    assert event.inputs == {"left": "price", "right": "qty"}
    assert event.output == "total"
    assert event.before_value is None
    assert event.after_value == 20
    assert event.metadata == {"operation": "multiply"}

    # Dict-compatibility checks
    assert isinstance(event, dict)
    assert event["type"] == "column_created"
    assert event["event_type"] == "column_created"
    assert event["dataframe_id"] == "df_001"
    assert event["source_dataframe_id"] == "df_000"
    assert event["column"] == "total"
    assert event["after_value"] == 20
    assert event["operation"] == "multiply"
    assert event["left"] == "price"


def test_provenance_event_from_dict():
    legacy_dict = {
        "type": "column_filled",
        "dataframe_id": "df_123",
        "column": "age",
        "value": 0,
        "missing_rows": [1, 2],
    }

    event = ProvenanceEvent.from_dict(legacy_dict)

    assert isinstance(event, ProvenanceEvent)
    assert isinstance(event, dict)
    assert event.event_type == "column_filled"
    assert event.object_id == "df_123"
    assert event.output == "age"
    assert event.metadata.get("value") == 0 or event.get("value") == 0
    assert event["type"] == "column_filled"
    assert event["dataframe_id"] == "df_123"
    assert event["column"] == "age"
    assert event["value"] == 0
    assert event["missing_rows"] == [1, 2]


def test_history_normalizes_dicts_to_provenance_events():
    history.clear()

    legacy_dict = {
        "type": "filter",
        "dataframe_id": "df_99",
        "column": "status",
        "operator": "==",
        "value": "active",
    }

    history.add(legacy_dict)

    all_events = history.get_all()
    assert len(all_events) == 1
    stored = all_events[0]

    assert isinstance(stored, ProvenanceEvent)
    assert isinstance(stored, dict)
    assert stored.event_type == "filter"
    assert stored.object_id == "df_99"
    assert stored.output == "status"
    assert stored["operator"] == "=="
    assert stored["value"] == "active"

    history.clear()


def test_provenance_event_to_dict():
    event = ProvenanceEvent(
        event_type="test_op",
        object_id="obj_1",
        output="out_col",
    )

    d = event.to_dict()
    assert isinstance(d, dict)
    assert not isinstance(d, ProvenanceEvent)
    assert d["type"] == "test_op"
    assert d["dataframe_id"] == "obj_1"
    assert d["column"] == "out_col"
