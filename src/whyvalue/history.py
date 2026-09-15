from .provenance import ProvenanceEvent


class History:
    def __init__(self):
        self.events = []

    def add(self, event):
        if not isinstance(event, ProvenanceEvent):
            event = ProvenanceEvent.from_dict(event)
        self.events.append(event)

    def get_all(self):
        return self.events

    def clear(self):
        self.events.clear()


history = History()
