"""Common provenance event model for WhyValue.

Represents transformation, lineage, and execution events across data sources
and data structures.
"""

from typing import Any, Dict, Optional, Union


class ProvenanceEvent(dict):
    """Unified provenance event model for WhyValue.

    Represents an event in a provenance history chain. Subclasses `dict` to
    maintain 100% backward compatibility with dictionary-based event access.

    Attributes:
        event_type: The operation or event category (e.g. 'column_created', 'fillna', 'filter').
        object_id: Unique lineage ID of the target object/DataFrame.
        source_id: Unique lineage ID of the source/parent object if applicable.
        inputs: Input operands, arguments, or source fields.
        output: Name or key of the output target (e.g. column name).
        before_value: Optional snapshot of value before operation.
        after_value: Optional snapshot of value after operation.
        metadata: Operation parameters and adapter-specific metadata.
    """

    def __init__(
        self,
        event_type: str,
        object_id: Optional[str] = None,
        source_id: Optional[str] = None,
        inputs: Optional[Dict[str, Any]] = None,
        output: Optional[Any] = None,
        before_value: Optional[Any] = None,
        after_value: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        super().__init__()

        self.event_type = event_type
        self.object_id = object_id
        self.source_id = source_id
        self.inputs = dict(inputs) if inputs is not None else {}
        self.output = output
        self.before_value = before_value
        self.after_value = after_value
        self.metadata = dict(metadata) if metadata is not None else {}

        # Backward compatibility dictionary mapping
        self["type"] = event_type
        self["event_type"] = event_type

        if object_id is not None:
            self["object_id"] = object_id
            self["dataframe_id"] = object_id

        if source_id is not None:
            self["source_id"] = source_id
            self["source_dataframe_id"] = source_id

        if output is not None:
            self["output"] = output
            self["column"] = output

        if before_value is not None:
            self["before_value"] = before_value

        if after_value is not None:
            self["after_value"] = after_value

        if self.inputs:
            self["inputs"] = self.inputs
            for k, v in self.inputs.items():
                if k not in self:
                    self[k] = v

        if self.metadata:
            self["metadata"] = self.metadata
            for k, v in self.metadata.items():
                if k not in self:
                    self[k] = v

        for k, v in kwargs.items():
            self[k] = v

    @classmethod
    def from_dict(cls, data: Union[dict, "ProvenanceEvent"]) -> "ProvenanceEvent":
        """Convert a dictionary or raw event into a ProvenanceEvent instance."""
        if isinstance(data, ProvenanceEvent):
            return data

        d = dict(data)
        event_type = d.pop("type", d.pop("event_type", "unknown"))
        object_id = d.pop("dataframe_id", d.pop("object_id", None))
        source_id = d.pop("source_dataframe_id", d.pop("source_id", None))
        output = d.pop("column", d.pop("output", None))
        before_value = d.pop("before_value", None)
        after_value = d.pop("after_value", None)

        inputs = d.pop("inputs", {})
        metadata = d.pop("metadata", {})

        remaining = dict(d)

        return cls(
            event_type=event_type,
            object_id=object_id,
            source_id=source_id,
            inputs=inputs,
            output=output,
            before_value=before_value,
            after_value=after_value,
            metadata=metadata,
            **remaining,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of this event."""
        return dict(self)
