"""Regression tests: GameState serialization must not wipe agent inventories.

Inventory (fle/env/entities.py) is a pydantic model with extra="allow", so
item counts live in __pydantic_extra__ and `inventory.__dict__` is always {}.
GameState.to_raw() and the reset tool client previously serialized
inventories via __dict__, which silently emptied every agent inventory in
saved snapshots and on every GameState restore.
"""

import json

from fle.commons.models.game_state import GameState
from fle.env.entities import Inventory


class TestGameStateToRaw:
    def test_preserves_pydantic_extra_inventories(self):
        gs = GameState(
            entities="abc",
            inventories=[Inventory(**{"iron-plate": 10, "coal": 5})],
            research=None,
        )
        raw = json.loads(gs.to_raw())
        assert raw["inventories"] == [{"iron-plate": 10, "coal": 5}]

    def test_accepts_plain_dict_inventories(self):
        gs = GameState(entities="abc", inventories=[{"stone": 3}], research=None)
        raw = json.loads(gs.to_raw())
        assert raw["inventories"] == [{"stone": 3}]

    def test_multiagent_roundtrip_through_parse_raw(self):
        gs = GameState(
            entities="abc",
            inventories=[
                Inventory(**{"iron-plate": 10}),
                Inventory(**{"copper-cable": 7, "coal": 1}),
            ],
            research=None,
        )
        restored = GameState.parse_raw(gs.to_raw())
        assert restored.inventories == [
            {"iron-plate": 10},
            {"copper-cable": 7, "coal": 1},
        ]


class TestResetClientInventorySerialization:
    def test_inventory_objects_serialize_to_item_counts(self):
        """The reset tool sends inventories to Lua as JSON; Inventory objects
        must serialize to their item counts, not to an empty __dict__."""
        from fle.env.tools.admin.reset.client import Reset

        # Replicate the client's serialization logic on a mixed input list
        # without needing a live connection: exercise __call__'s conversion
        # by monkeypatching execute.
        captured = {}

        class FakeReset(Reset):
            def __init__(self):  # bypass Tool/connection setup entirely
                pass

            def execute(self, inventories_json, *args):
                captured["json"] = inventories_json
                return True, 0.0

        FakeReset()(
            inventories=[Inventory(**{"iron-plate": 4}), {"stone": 2}],
            reset_position=False,
        )
        sent = json.loads(captured["json"])
        assert sent == [{"iron-plate": 4}, {"stone": 2}]
