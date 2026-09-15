import copy
import uuid

from ..history import history
from ..provenance import ProvenanceEvent


class TrackedDict(dict):
    """Tracked Python dictionary subclass recording provenance events."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._whyvalue_id = uuid.uuid4().hex

    def __deepcopy__(self, memo):
        rv = dict()
        memo[id(self)] = rv
        for k, v in self.items():
            rv[copy.deepcopy(k, memo)] = copy.deepcopy(v, memo)
        return rv

    def __setitem__(self, key, value):
        from ..core import is_snapshot_enabled

        snapshot = is_snapshot_enabled()
        before = copy.deepcopy(dict(self)) if snapshot else None
        super().__setitem__(key, value)
        after = copy.deepcopy(dict(self)) if snapshot else None
        history.add(
            ProvenanceEvent(
                event_type="dict_setitem",
                object_id=self._whyvalue_id,
                output=key,
                before_value=before,
                after_value=after,
                inputs={"key": key, "value": value},
                metadata={"operation": "setitem", "key": key, "value": value},
            )
        )

    def __delitem__(self, key):
        from ..core import is_snapshot_enabled

        snapshot = is_snapshot_enabled()
        before = copy.deepcopy(dict(self)) if snapshot else None
        super().__delitem__(key)
        after = copy.deepcopy(dict(self)) if snapshot else None
        history.add(
            ProvenanceEvent(
                event_type="dict_delitem",
                object_id=self._whyvalue_id,
                output=key,
                before_value=before,
                after_value=after,
                inputs={"key": key},
                metadata={"operation": "delitem", "key": key},
            )
        )

    def update(self, *args, **kwargs):
        from ..core import is_snapshot_enabled

        snapshot = is_snapshot_enabled()
        before = copy.deepcopy(dict(self)) if snapshot else None
        other = dict(*args, **kwargs)
        super().update(other)
        after = copy.deepcopy(dict(self)) if snapshot else None
        history.add(
            ProvenanceEvent(
                event_type="dict_update",
                object_id=self._whyvalue_id,
                before_value=before,
                after_value=after,
                inputs={"update_dict": copy.deepcopy(other)},
                metadata={"operation": "update", "update": copy.deepcopy(other)},
            )
        )

    def pop(self, key, *args):
        from ..core import is_snapshot_enabled

        existed = key in self
        snapshot = is_snapshot_enabled()
        before = copy.deepcopy(dict(self)) if snapshot else None
        res = super().pop(key, *args)
        if existed:
            after = copy.deepcopy(dict(self)) if snapshot else None
            history.add(
                ProvenanceEvent(
                    event_type="dict_pop",
                    object_id=self._whyvalue_id,
                    output=key,
                    before_value=before,
                    after_value=after,
                    inputs={"key": key},
                    metadata={"operation": "pop", "key": key, "removed_value": res},
                )
            )
        return res

    def popitem(self):
        from ..core import is_snapshot_enabled

        snapshot = is_snapshot_enabled()
        before = copy.deepcopy(dict(self)) if snapshot else None
        k, v = super().popitem()
        after = copy.deepcopy(dict(self)) if snapshot else None
        history.add(
            ProvenanceEvent(
                event_type="dict_popitem",
                object_id=self._whyvalue_id,
                output=k,
                before_value=before,
                after_value=after,
                inputs={"key": k, "value": v},
                metadata={"operation": "popitem", "key": k, "value": v},
            )
        )
        return k, v

    def setdefault(self, key, default=None):
        from ..core import is_snapshot_enabled

        already_exists = key in self
        snapshot = is_snapshot_enabled()
        before = copy.deepcopy(dict(self)) if snapshot else None
        res = super().setdefault(key, default)
        after = copy.deepcopy(dict(self)) if snapshot else None
        history.add(
            ProvenanceEvent(
                event_type="dict_setdefault",
                object_id=self._whyvalue_id,
                output=key,
                before_value=before,
                after_value=after,
                inputs={
                    "key": key,
                    "default": default,
                    "inserted": not already_exists,
                    "value": res,
                },
                metadata={
                    "operation": "setdefault",
                    "key": key,
                    "default": default,
                    "inserted": not already_exists,
                    "value": res,
                },
            )
        )
        return res

    def clear(self):
        from ..core import is_snapshot_enabled

        snapshot = is_snapshot_enabled()
        before = copy.deepcopy(dict(self)) if snapshot else None
        super().clear()
        after = copy.deepcopy(dict(self)) if snapshot else None
        history.add(
            ProvenanceEvent(
                event_type="dict_clear",
                object_id=self._whyvalue_id,
                before_value=before,
                after_value=after,
                metadata={"operation": "clear"},
            )
        )
