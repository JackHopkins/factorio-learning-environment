from dataclasses import dataclass
from typing import List, Dict, Union, Optional

from entities import Entity, EntityGroup


@dataclass
class Trace:
    program: str
    output: List[str]
    result: str
    starting_inventory: Dict[str, int]
    mining_setup: List[Union[Entity, EntityGroup]]
    messages: List[str]
    planning: bool
    full_output: str
    success: bool
    target_pl: Dict[str, Dict[str, int]]
    task_description: str
    achieved_pl: Dict[str, Dict[str, int]]
    task_number: Optional[int] = 0

    def __repr__(self):
        return f"{'Successful ' if self.success else ''}Trace(program={self.program}, output={self.output}, result={self.result}, " \
               f"starting_inventory={self.starting_inventory}, mining_setup={self.mining_setup}, " \
               f"messages={self.messages}, planning={self.planning}, full_output={self.full_output}, " \
               f"success={self.success}, target_pl={self.target_pl}, task_description={self.task_description}, " \
               f"achieved_pl={self.achieved_pl}, task_number={self.task_number}"
