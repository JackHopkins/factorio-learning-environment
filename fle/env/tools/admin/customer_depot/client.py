from typing import Any

from fle.env.tools import Tool


class CustomerDepot(Tool):
    """Admin interface to customer-owned sink depots (contract fulfillment)."""

    def __call__(
        self,
        command: str = "telemetry",
        x: float = 0,
        y: float = 0,
        chest_count: int = 8,
        relative: bool = True,
    ) -> dict[str, Any]:
        response, _ = self.execute(
            self.player_index, command, x, y, chest_count, relative
        )
        return response

    def place(self, x: float, y: float, chest_count: int = 8) -> dict[str, Any]:
        return self.__call__("place", x, y, chest_count)

    def telemetry(self) -> dict[str, Any]:
        return self.__call__("telemetry")

    def clear(self) -> dict[str, Any]:
        return self.__call__("clear")
