from typing import Any

from fle.env.tools import Tool


class Perturbation(Tool):
    """Admin interface for hidden world disruptions (shock track)."""

    def __call__(
        self, command: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        response, _ = self.execute(self.player_index, command, parameters or {})
        return response
