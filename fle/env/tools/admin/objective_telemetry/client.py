from fle.env.tools import Tool


class ObjectiveTelemetry(Tool):
    """Read or reset authoritative rollout telemetry maintained by Factorio."""

    def __call__(self, reset: bool = False):
        response, _ = self.execute(self.player_index, reset)
        return response
