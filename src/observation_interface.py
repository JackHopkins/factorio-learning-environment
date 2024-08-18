from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Union

class FactorioObservationInterface(ABC):

    @abstractmethod
    def get_map_state(self, area: Tuple[Tuple[float, float], Tuple[float, float]]) -> Dict[str, Union[str, Tuple[float, float]]]:
        pass

    @abstractmethod
    def get_resources(self, area: Tuple[Tuple[float, float], Tuple[float, float]]) -> List[Dict[str, Union[str, Tuple[float, float], int]]]:
        pass

    @abstractmethod
    def get_entities(self, area: Tuple[Tuple[float, float], Tuple[float, float]], entity_type: str = None) -> List[Dict[str, Union[int, str, Tuple[float, float]]]]:
        pass

    @abstractmethod
    def get_technology_tree(self) -> Dict[str, Dict[str, Union[List[str], int]]]:
        pass

    @abstractmethod
    def get_logistics_network(self, force: str = None) -> Dict[str, Dict[str, int]]:
        pass

    @abstractmethod
    def get_crafting_recipes(self) -> Dict[str, Dict[str, Union[str, List[str]]]]:
        pass

    @abstractmethod
    def get_player_state(self) -> Dict[str, Union[float, int, Tuple[float, float]]]:
        pass
