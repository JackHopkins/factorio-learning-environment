from enum import Enum
from typing import Literal

from pydantic import BaseModel

class Roles(Enum):
    assistant = 'assistant'
    system = 'system'
    user = 'user'

class Slot(BaseModel):
    role: Roles
    content: str
    name: str