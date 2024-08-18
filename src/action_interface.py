from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Union

class ActionInterface(ABC):

    @abstractmethod
    def get_nearest(self, structure_type: str, position: Tuple[float, float], direction: str) -> None:
        pass

    @abstractmethod
    def goto(self, structure_type: str, position: Tuple[float, float], direction: str) -> None:
        pass

    @abstractmethod
    def build(self, structure_type: str, position: Tuple[float, float], direction: str) -> None:
        pass

    @abstractmethod
    def craft(self, item_type: str, quantity: int) -> None:
        pass

    @abstractmethod
    def research(self, technology: str) -> None:
        pass

    @abstractmethod
    def control(self, entity_id: int, action: str, parameters: Dict[str, Union[str, int]]) -> None:
        pass

    @abstractmethod
    def manage_inventory(self, action: str, item_type: str, parameters: Dict[str, Union[int, Tuple[int, int]]]) -> None:
        pass

    @abstractmethod
    def blueprint(self, action: str, blueprint_data: Dict[str, Union[str, List[Dict[str, Union[str, Tuple[float, float], int]]]]]) -> None:
        pass

    @abstractmethod
    def deconstruct(self, target: Union[int, Tuple[Tuple[float, float], Tuple[float, float]]]) -> None:
        pass
