from __future__ import annotations

import json
from typing import Any, Dict, Optional

from fle.env.tools import Tool


class Cutscene(Tool):
    """Python wrapper for the cutscene admin action.

    This mirrors the existing admin tool pattern: payloads are JSON-serialised and
    dispatched through ``Controller.execute`` which invokes ``global.actions.cutscene``
    in the loaded Lua runtime.

    The Lua handler provides:
    - Plan submission with automatic lifecycle management
    - State management and tracking
    - Screenshot capture coordination
    - Query APIs for status and statistics
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
        return self.submit_plan(plan)

    def submit_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a complete cutscene plan."""
        payload = json.dumps(plan)
        response, _ = self.execute(payload)
        return response

    def submit_shot(
        self,
        shot: Dict[str, Any],
        player: int = 1,
        capture_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a single shot as a minimal plan.

        Args:
            shot: Shot intent dictionary with kind, timing, zoom, etc.
            player: Player index (default 1)
            capture_dir: Optional capture directory

        Returns:
            Response from plan submission
        """
        plan = {
            "player": player,
            "shots": [shot],
            "capture": True,
        }
        if capture_dir:
            plan["capture_dir"] = capture_dir

        return self.submit_plan(plan)

    def get_status(self, player: int = 1) -> Dict[str, Any]:
        """Get the current cutscene status for a player.

        Returns:
            Status dictionary with active plan info, or None if no active plan
        """
        cmd = f"/c return global.actions.cutscene_status({player})"
        result = self.lua_script_manager.rcon_client.send_command(cmd)
        if result:
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                pass
        return {"ok": False, "error": "failed to get status"}

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the cutscene system.

        Returns:
            Stats dictionary with counts, capture info, etc.
        """
        cmd = "/c return global.actions.cutscene_stats()"
        result = self.lua_script_manager.rcon_client.send_command(cmd)
        if result:
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                pass
        return {"ok": False, "error": "failed to get stats"}

    def cancel(self, player: int = 1) -> Dict[str, Any]:
        """Cancel the active cutscene for a player.

        Args:
            player: Player index

        Returns:
            Response indicating success/failure
        """
        cmd = f"/c return global.actions.cutscene_cancel({player})"
        result = self.lua_script_manager.rcon_client.send_command(cmd)
        if result:
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                pass
        return {"ok": False, "error": "failed to cancel"}

    def start_recording(
        self,
        player: int = 1,
        session_id: Optional[str] = None,
        capture_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start a recording session (screenshot capture without cutscene).

        Args:
            player: Player index
            session_id: Optional session identifier
            capture_dir: Optional capture directory

        Returns:
            Response with session_id
        """
        payload = {"player_index": player}
        if session_id:
            payload["session_id"] = session_id
        if capture_dir:
            payload["capture_dir"] = capture_dir

        result = self.lua_script_manager.rcon_client.send_command(
            f"/c return global.actions.start_recording('{json.dumps(payload)}')"
        )
        if result:
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                pass
        return {"ok": False, "error": "failed to start recording"}

    def stop_recording(self) -> Dict[str, Any]:
        """Stop the current recording session.

        Returns:
            Response with session_id of stopped session
        """
        result = self.lua_script_manager.rcon_client.send_command(
            "/c return global.actions.stop_recording()"
        )
        if result:
            try:
                return json.loads(result)
            except (json.JSONDecodeError, TypeError):
                pass
        return {"ok": False, "error": "failed to stop recording"}
