import copy
import uuid

from ..history import history
from ..provenance import ProvenanceEvent


class TrackedList(list):
    """Tracked Python list subclass recording provenance events."""

    def __init__(self, iterable=()):
        super().__init__(iterable)
        self._whyvalue_id = uuid.uuid4().hex

    def __deepcopy__(self, memo):
        rv = []
        memo[id(self)] = rv
        for item in self:
            rv.append(copy.deepcopy(item, memo))
        return rv

    def append(self, value):
        from ..core import is_snapshot_enabled

        snapshot = is_snapshot_enabled()
        before = copy.deepcopy(list(self)) if snapshot else None
        super().append(value)
        after = copy.deepcopy(list(self)) if snapshot else None
        history.add(
            ProvenanceEvent(
                event_type="list_append",
                object_id=self._whyvalue_id,
                before_value=before,
                after_value=after,
                inputs={"value": value},
                metadata={"operation": "append", "value": value},
            )
        )

    def extend(self, iterable):
        from ..core import is_snapshot_enabled

        snapshot = is_snapshot_enabled()
        before = copy.deepcopy(list(self)) if snapshot else None
        items_to_add = list(iterable)
        super().extend(items_to_add)
        after = copy.deepcopy(list(self)) if snapshot else None
        history.add(
            ProvenanceEvent(
                event_type="list_extend",
                object_id=self._whyvalue_id,
                before_value=before,
                after_value=after,
                inputs={"iterable": items_to_add},
                metadata={"operation": "extend", "values": items_to_add},
            )
        )

    def insert(self, index, value):
        from ..core import is_snapshot_enabled

        snapshot = is_snapshot_enabled()
        before = copy.deepcopy(list(self)) if snapshot else None
        super().insert(index, value)
        after = copy.deepcopy(list(self)) if snapshot else None
        history.add(
            ProvenanceEvent(
                event_type="list_insert",
                object_id=self._whyvalue_id,
                before_value=before,
                after_value=after,
                inputs={"index": index, "value": value},
                metadata={"operation": "insert", "index": index, "value": value},
            )
        )

    def remove(self, value):
        from ..core import is_snapshot_enabled

        snapshot = is_snapshot_enabled()
        before = copy.deepcopy(list(self)) if snapshot else None
        super().remove(value)
        after = copy.deepcopy(list(self)) if snapshot else None
        history.add(
            ProvenanceEvent(
                event_type="list_remove",
                object_id=self._whyvalue_id,
                before_value=before,
                after_value=after,
                inputs={"value": value},
                metadata={"operation": "remove", "value": value},
            )
        )

    def pop(self, index=-1):
        from ..core import is_snapshot_enabled

        snapshot = is_snapshot_enabled()
        before = copy.deepcopy(list(self)) if snapshot else None
        res = super().pop(index)
        after = copy.deepcopy(list(self)) if snapshot else None
        history.add(
            ProvenanceEvent(
                event_type="list_pop",
                object_id=self._whyvalue_id,
                before_value=before,
                after_value=after,
                inputs={"index": index},
                metadata={"operation": "pop", "index": index, "removed_value": res},
            )
        )
        return res

    def clear(self):
        from ..core import is_snapshot_enabled

        snapshot = is_snapshot_enabled()
        before = copy.deepcopy(list(self)) if snapshot else None
        super().clear()
        after = copy.deepcopy(list(self)) if snapshot else None
        history.add(
            ProvenanceEvent(
                event_type="list_clear",
                object_id=self._whyvalue_id,
                before_value=before,
                after_value=after,
                metadata={"operation": "clear"},
            )
        )

    def __setitem__(self, index, value):
        from ..core import is_snapshot_enabled

        snapshot = is_snapshot_enabled()
        before = copy.deepcopy(list(self)) if snapshot else None
        super().__setitem__(index, value)
        after = copy.deepcopy(list(self)) if snapshot else None
        history.add(
            ProvenanceEvent(
                event_type="list_setitem",
                object_id=self._whyvalue_id,
                before_value=before,
                after_value=after,
                inputs={"index": index, "value": value},
                metadata={"operation": "setitem", "index": index, "value": value},
            )
        )

    def __delitem__(self, index):
        from ..core import is_snapshot_enabled

        snapshot = is_snapshot_enabled()
        before = copy.deepcopy(list(self)) if snapshot else None
        super().__delitem__(index)
        after = copy.deepcopy(list(self)) if snapshot else None
        history.add(
            ProvenanceEvent(
                event_type="list_delitem",
                object_id=self._whyvalue_id,
                before_value=before,
                after_value=after,
                inputs={"index": index},
                metadata={"operation": "delitem", "index": index},
            )
        )
