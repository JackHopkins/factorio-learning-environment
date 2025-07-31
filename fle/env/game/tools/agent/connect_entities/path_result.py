from typing import Dict, Union


class PathResult:
    """Encapsulates the result of a path finding operation"""

    def __init__(self, response: Union[Dict, str]):
        self.raw_response = response
        self.is_success = isinstance(response, dict)
        self.error_message = response if isinstance(response, str) else None
        self.entities = response.get("entities", {}) if self.is_success else {}
        self.connected = response.get("connected", False) if self.is_success else False

    @property
    def required_entities(self) -> int:
        return self.raw_response.get("number_of_entities", 0) if self.is_success else 0
