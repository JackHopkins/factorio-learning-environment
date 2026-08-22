from typing import Any

from fle.env.tools import Tool


class EntityCensus(Tool):
    """Aggregate entity counts by name and status (no full serialization)."""

    def __call__(self) -> dict[str, Any]:
        response, _ = self.execute(self.player_index)
        return response
