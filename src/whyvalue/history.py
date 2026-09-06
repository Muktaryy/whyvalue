class History:
    def __init__(self):
        self.events = []

    def add(self, event):
        self.events.append(event)

    def get_all(self):
        return self.events

    def clear(self):
        self.events.clear()


history = History()
