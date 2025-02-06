from pydantic import BaseModel


class EventType:
    VARIABLE = 1
    WARNING = 2
    ERROR = 3
    COMMAND = 4
    OBSERVATION = 5