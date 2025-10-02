from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fle.env.tools import Tool


class Cutscene(Tool):
    """Python wrapper for the cutscene admin action.

    This mirrors the existing admin tool pattern: payloads are JSON-serialised and
    dispatched through ``Controller.execute`` which invokes ``global.actions.cutscene``
    in the loaded Lua runtime. The Lua handler supports a single mode:

    - Submit a cutscene plan for immediate execution with automatic lifecycle management.

    Cutscenes are fire-and-forget: submit a plan and it executes automatically.
    Screenshot capture is controlled by the plan.capture flag.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def __call__(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a cutscene plan for immediate execution.

        Args:
            plan: Dictionary matching the ShotIntent plan contract. Must include:
                - player: Player index or name
                - shots: List of shot intents
                - capture: Optional boolean to enable screenshot capture

        Returns:
            Response dictionary from the Lua handler. On success it contains
            ``{"ok": True, "plan_id": "...", "started": True}``.
        """
        payload = json.dumps(plan)
        response, _ = self.execute(payload)
        return response
