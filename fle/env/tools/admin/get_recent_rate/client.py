from typing import Any

from fle.env.tools import Tool


class GetRecentRate(Tool):
    """Cheap privileged production-rate query backed by LuaFlowStatistics."""

    def __call__(self, item_name: str, window_seconds: int = 5) -> dict[str, Any]:
        response, _ = self.execute(self.player_index, item_name, window_seconds)
        return response
