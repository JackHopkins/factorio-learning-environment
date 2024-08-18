import json

from rich.table import Table

from models.event_type import EventType
from models.memory import Memory


def remove_alternating_duplicates(lst):
    """
    Remove alternating duplicates from a list
    :param lst:
    :return:
    """
    return lst[::2] if lst[::2] == lst[1::2] else lst

class SplitMemory(Memory):
    """
    This only provides views of the last N action / observation loops.
    """

    def __init__(self, max_observations=5,
                 max_commands=10,
                 max_errors=5,
                 ignore_members=[],
                 run=None,
                 score_threshold=5,
                 llama_file='llama_events.jsonl'):
        super().__init__(size=10,
                         max_history=max_commands,
                         ignore_members=ignore_members,
                         llama_file=llama_file,
                         score_threshold=score_threshold,
                         run=run)
        self.observations = []
        self.commands = []
        self.errors = []
        self.warnings = []
        self.max_observations = max_observations
        self.max_history = max_commands
        self.variable_prompt = "Variables: "
        self.warning_prompt = "Warnings: "
        self.command_prompt = "Recent History: "

        self.table = Table(show_header=True, header_style="bold magenta")
        self.table.add_column("Score")
        self.table.add_column("Recent Commands")
        self.console.set_live(self.table)


    def get_events(self):
        #latest_variable_event = self.get_last_events(filters=[EventType.VARIABLE], number=1)
        #if latest_variable_event and self.variable_prompt not in latest_variable_event[0].message:
        #    latest_variable_event[0].message = f"{self.variable_prompt}\n{latest_variable_event[0].message}"

        # latest_warning_event = self.get_last_events(filters=[EventType.WARNING], number=1)
        # if latest_warning_event and self.warning_prompt not in latest_warning_event[0].message:
        #     latest_warning_event[0].message = f"{self.warning_prompt}\n{latest_warning_event[0].message}"

        events = self.get_last_events(filters=[EventType.COMMAND, EventType.OBSERVATION, EventType.WARNING, EventType.ERROR, EventType.VARIABLE],
                                      number=self.max_history)

        # compress duplicate events from last backwards
        last_event = None
        unfiltered_events = []
        for event in events:
            if event.message != last_event:
                #events.remove(event)
                unfiltered_events.append(event)
            last_event = event.message

        # remove alternating duplicates

        # remove historical warnings from the past
        events = unfiltered_events

        for event in events:
            self.table.add_row(
                str(event.score), event.message
            )
        #if events and self.command_prompt not in events[0].message:
        #    events[0].message = f"{self.command_prompt}\n{events[0].message}"

        #all_events = latest_warning_event + events

        return events #all_events

    def __next__(self):
        events = self.get_events()
        messages = self.get_messages(events)
        return messages
