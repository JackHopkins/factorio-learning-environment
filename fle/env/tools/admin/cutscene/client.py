from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fle.env.tools import Tool


class Cutscene(Tool):
    """Python wrapper for the cutscene admin action.

    This mirrors the existing admin tool pattern: payloads are JSON-serialised and
    dispatched through ``Controller.execute`` which invokes ``global.actions.cutscene``
    in the loaded Lua runtime.  The Lua handler understands three modes:

    - queue (default): enqueue and eventually start a plan for the target player.
    - report: fetch the latest lifecycle report for a previously submitted plan.
    - cancel: abort the currently active plan for the target player.

    The convenience methods below cover these behaviours while keeping the public
    API straightforward for downstream callers (tests, replay pipelines, etc.).
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    # ---- Queue / submit ------------------------------------------------- #
    def __call__(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Queue a cinematics plan for the target player.

        Args:
            plan: Dictionary matching the ShotIntent plan contract described in
                ``cinema.md``.  The Lua side performs full validation and returns a
                status payload.

        Returns:
            Response dictionary from the Lua handler. On success it contains
            ``{"ok": True, "queued": True, "plan_id": ...}``.
        """

        return self.queue_plan(plan)

    def queue_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        payload = json.dumps(plan)
        response, _ = self.execute(payload)
        # The execute method returns the parsed response, not a list
        return response

    # ---- Reporting ------------------------------------------------------ #
    def fetch_report(self, plan_id: str, player: Any) -> Dict[str, Any]:
        """Fetch the latest lifecycle report for a plan."""

        payload = {
            "mode": "report",
            "plan_id": plan_id,
            "player": player,
        }
        response, _ = self.execute(json.dumps(payload))
        return response

    # ---- Plan Control --------------------------------------------------- #
    def start_plan(self, plan_id: str, player: Any) -> Dict[str, Any]:
        """Start a queued plan for the given player."""
        # Plans are automatically started when queued, so just return success
        return {"ok": True, "message": "Plan queued and will start automatically"}

    def cancel_plan(self, player: Any) -> Dict[str, Any]:
        """Cancel the currently active plan for the given player."""

        payload = {
            "mode": "cancel",
            "player": player,
        }
        response, _ = self.execute(json.dumps(payload))
        return response

    # ---- Convenience helpers ------------------------------------------- #
    def queue_and_wait(
        self,
        plan: Dict[str, Any],
        poll_interval_s: float = 0.5,
        timeout_s: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Submit a plan and poll for completion.

        Lua does not currently provide a direct blocking wait, so polling via
        ``fetch_report`` remains the simplest option for acceptance tests.
        """

        import time

        result = self.queue_plan(plan)
        if not result.get("ok"):
            return result

        plan_id = result.get("plan_id")
        if not plan_id:
            return result

        elapsed = 0.0
        while timeout_s is None or elapsed < timeout_s:
            report = self.fetch_report(plan_id, plan.get("player"))
            report_data = report.get("report") if report.get("ok") else None
            if report_data and (
                report_data.get("finished") or report_data.get("cancelled")
            ):
                return report
            time.sleep(poll_interval_s)
            elapsed += poll_interval_s

        return {
            "ok": False,
            "error": "timeout waiting for plan completion",
            "plan_id": plan_id,
        }
