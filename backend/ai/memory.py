# ai/memory.py

class EngineerMemory:

    def __init__(self):
        self.last_events = []

    def should_generate(self, events):

        if events == self.last_events:
            return False

        self.last_events = events.copy()
        return True