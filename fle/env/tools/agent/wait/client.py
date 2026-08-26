from time import sleep as wall_sleep
from typing import Any

from fle.env.tools import Tool
from fle.env.tools.agent.sleep.client import Sleep


class Wait(Tool):
    """Advance the live simulation, optionally until an inventory condition holds."""

    def __call__(
        self,
        ticks: int,
        until: dict[str, Any] | None = None,
        poll_ticks: int = 300,
    ) -> dict[str, Any]:
        requested_ticks = self._positive_int("ticks", ticks)
        polling_ticks = self._positive_int("poll_ticks", poll_ticks)
        condition = self._validate_condition(until)

        action_ticks_before = self.game_state.instance.get_elapsed_ticks()
        start_game_tick, _ = self.execute(0)
        condition_met, observed = self._check_condition(condition)
        waited_ticks = 0

        while waited_ticks < requested_ticks and not condition_met:
            chunk_ticks = min(polling_ticks, requested_ticks - waited_ticks)
            self.execute(chunk_ticks)
            waited_ticks += chunk_ticks

            game_speed = self.game_state.instance.get_speed()
            real_world_sleep = chunk_ticks / 60 / game_speed if game_speed > 0 else 0
            if real_world_sleep > 0:
                wall_sleep(real_world_sleep)
                Sleep._add_sleep_duration(real_world_sleep)

            condition_met, observed = self._check_condition(condition)

        end_game_tick, _ = self.execute(0)
        action_ticks_after = self.game_state.instance.get_elapsed_ticks()
        return {
            "requested_ticks": requested_ticks,
            "waited_ticks": waited_ticks,
            "simulation_ticks_advanced": max(int(end_game_tick) - int(start_game_tick), 0),
            "action_ticks_charged": max(action_ticks_after - action_ticks_before, 0),
            "condition_met": condition_met if condition is not None else None,
            "observed": observed,
        }

    @staticmethod
    def _positive_int(name: str, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")
        return value

    @staticmethod
    def _validate_condition(until: dict[str, Any] | None) -> dict[str, Any] | None:
        if until is None:
            return None
        if not isinstance(until, dict) or set(until) != {"inventory"}:
            raise ValueError("until must contain exactly one 'inventory' condition")
        inventory = until["inventory"]
        required = {"entity", "item", "at_least"}
        if not isinstance(inventory, dict) or set(inventory) != required:
            raise ValueError(
                "until['inventory'] must contain entity, item, and at_least"
            )
        if (
            isinstance(inventory["at_least"], bool)
            or not isinstance(inventory["at_least"], int)
            or inventory["at_least"] < 0
        ):
            raise ValueError("until['inventory']['at_least'] must be a non-negative integer")
        return inventory

    def _check_condition(
        self, condition: dict[str, Any] | None
    ) -> tuple[bool, dict[str, Any] | None]:
        if condition is None:
            return False, None
        inventory = self.game_state.inspect_inventory(condition["entity"])
        count = int(inventory[condition["item"]])
        observed = {
            "kind": "inventory",
            "item": self._item_name(condition["item"]),
            "count": count,
            "at_least": condition["at_least"],
        }
        return count >= condition["at_least"], observed

    @staticmethod
    def _item_name(item: Any) -> str:
        if hasattr(item, "value"):
            value = item.value
            return str(value[0] if isinstance(value, tuple) else value)
        return str(item)
