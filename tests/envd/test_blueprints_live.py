import unittest

from fle.env.entities import Position
from fle.env.game_types import Prototype
from fle.envd.backend import FLEWorker
from fle.envd.blueprints import BlueprintStore
from fle.envd.models import FactorioTaskSpec

SCOPE = "live-blueprint-gen"


class TestBlueprintsLive(unittest.TestCase):
    """Save -> persist across leases -> place-by-name against live Factorio."""

    def _worker(self) -> FLEWorker:
        return FLEWorker.connect("live-blueprint-worker", tcp_port=27000)

    def _task(self) -> FactorioTaskSpec:
        return FactorioTaskSpec(
            task_id="blueprint_live_v1",
            goal="Build reusable factory fragments.",
            verifier={"implementation": "objective_engine_v1"},
            blueprint_scope=SCOPE,
            provisioning={"starting_inventory": {"transport-belt": 20}},
            max_interventions=8,
        )

    BUILD_AND_SAVE = """
# Find a contiguous free run so the captured blueprint is clean belts.
def find_run(n):
    for y in range(-14, 15, 2):
        run = 0
        start = None
        for x in range(-18, 19):
            if can_place_entity(Prototype.TransportBelt, position=Position(x=x, y=y)):
                if run == 0:
                    start = x
                run = run + 1
                if run >= n:
                    return Position(x=start, y=y)
            else:
                run = 0
    return None

spot = find_run(4)
if spot is None:
    print('no free run')
else:
    placed = 0
    for offset in range(4):
        pos = Position(x=spot.x + offset, y=spot.y)
        if place_entity(Prototype.TransportBelt, direction=Direction.RIGHT, position=pos):
            placed = placed + 1
    print('belts placed:', placed)
    saved = blueprint('save', name='pair-line', x=spot.x + 1, y=spot.y, radius=3)
    print('saved:', saved['entity_count'])
"""

    PLACE_BY_NAME = """
# Find a contiguous free run: blueprint placement skips entities that
# already exist at the destination, and revive fails on collisions, so the
# whole footprint must be open ground.
def find_run(n):
    for y in range(-14, 15, 2):
        run = 0
        start = None
        for x in range(-18, 19):
            if can_place_entity(Prototype.TransportBelt, position=Position(x=x, y=y)):
                if run == 0:
                    start = x
                run = run + 1
                if run >= n:
                    return Position(x=start, y=y)
            else:
                run = 0
    return None

spot = find_run(4)
if spot is None:
    print('no free run')
else:
    result = blueprint('place', 'pair-line', spot.x + 1, spot.y)
    print('placement:', result['placed'], result.get('source'))
"""

    def test_save_survives_lease_and_places_by_name(self):
        worker = self._worker()
        # Fresh scope so prior runs cannot satisfy the assertions.
        BlueprintStore(scope=SCOPE).drop_scope()
        try:
            # -- Episode 1: build two belts and save them -------------------
            worker.start_task(self._task())
            first = worker.execute("lease-a", self.BUILD_AND_SAVE, 1)
            self.assertFalse(first.event.error, msg=first.event.result)

            store = BlueprintStore(scope=SCOPE)
            record = store.get("pair-line")
            self.assertGreaterEqual(record.entity_count, 1)

            obs = worker.observe("lease-a")
            names = [entry.name for entry in obs.blueprints]
            self.assertIn("pair-line", names)
            worker.release()

            # -- Episode 2: fresh world, same scope, place by name ----------
            worker.start_task(self._task())
            second = worker.execute("lease-b", self.PLACE_BY_NAME, 1)
            self.assertFalse(second.event.error, msg=second.event.result)
            # The program prints 'placement: N source' on success; a missing
            # anchor or deduped placement would print differently.
            self.assertIn("placement:", second.event.result)

            namespace = worker.instance.first_namespace
            belts = namespace.get_entities(
                {Prototype.TransportBelt}, position=Position(x=0, y=0), radius=200
            )
            flat = []
            stack = list(belts)
            while stack:
                item = stack.pop()
                if isinstance(item, list):
                    stack.extend(item)
                else:
                    flat.append(item)
            # Originals from episode 1 were reset away; any belts visible now
            # came from the blueprint placement.
            self.assertGreaterEqual(len(flat), 1, msg=second.event.result)
            self.assertEqual(store.get("pair-line").times_placed, 1)

            content = store.get("pair-line").content
            inline = worker.execute(
                "lease-b",
                f"result = blueprint('place', {content!r}, -6, 4)\n"
                "print('inline done')",
                2,
            )
            self.assertFalse(inline.event.error, msg=inline.event.result)
        finally:
            BlueprintStore(scope=SCOPE).drop_scope()
            worker.release()


if __name__ == "__main__":
    unittest.main()
