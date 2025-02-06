from models.event_type import EventType
from models.memory import Memory


class NarrativeMemory(Memory):
    """
    This only provides views of the last N action / observation loops.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_events(self):
        return self.get_last_events(number=self.size)


    def __next__(self):
        messages = [{"role": "system", "content": self.brief}]

        events = self.get_events()

        for event in events:
            messages += [{
                "role": event.role,
                "content": event.message
            }]

        return messages
