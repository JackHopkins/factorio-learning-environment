import unittest

from fle.envd.backend import FLEWorker
from fle.envd.models import (
    DisruptionScheduleSpec,
    FactorioTaskSpec,
    PerturbationSpec,
    VerifierSpec,
)


class TestPerturbationsLive(unittest.TestCase):
    """Hidden disruptions against a live Factorio server."""

    def _worker(self) -> FLEWorker:
        return FLEWorker.connect("live-perturbation-worker", tcp_port=27000)

    def _task_spec(self) -> FactorioTaskSpec:
        return FactorioTaskSpec(
            task_id="perturbation_live_v1",
            goal="Survive hidden world disruptions.",
            verifier=VerifierSpec(implementation="objective_engine_v1"),
            perturbations=DisruptionScheduleSpec(
                perturbations=[
                    # Tick 0: part of the initial world; must apply during
                    # start_task, before the first observation.
                    PerturbationSpec(
                        perturbation_id="dis-000-deplete",
                        kind="resource_depletion",
                        trigger_tick=0,
                        parameters={"radius": 24},
                    ),
                    # Tick > 0: fires during the sync after the program has
                    # built its own targets. 600 ticks of unpaused simulation
                    # elapse within one intervention at speed 10x.
                    PerturbationSpec(
                        perturbation_id="dis-001-belt",
                        kind="entity_destruction",
                        trigger_tick=600,
                        parameters={
                            "entity_names": ["transport-belt"],
                            "count": 5,
                            "search_radius": 100,
                        },
                    ),
                ],
                recovery_min_ticks=600,
            ),
            provisioning={"starting_inventory": {"transport-belt": 20}},
            max_interventions=8,
            holdout_seconds=1,
        )

    # Disruption sync runs after the program inside execute(), so belts
    # placed here exist by the time the tick-600 shock fires. The sleeps
    # advance real simulation ticks (60 per second) while unpaused.
    SETUP_PROGRAM = """
placed = 0
for offset in range(-3, 4):
    pos = Position(x=offset, y=-2)
    if can_place_entity(Prototype.TransportBelt, position=pos):
        if place_entity(Prototype.TransportBelt, position=pos):
            placed = placed + 1
print('placed:', placed)
for i in range(12):
    sleep(1)
"""

    def test_disruptions_fire_and_are_recorded(self):
        worker = self._worker()
        task = self._task_spec()
        try:
            worker.start_task(task)

            # -- Pre-intervention shock: applied before any observation ----
            pre = [
                payload
                for payload in worker._disruption_events
                if payload["perturbation_id"] == "dis-000-deplete"
            ]
            self.assertEqual(len(pre), 1)
            self.assertIn(pre[0]["status"], {"applied", "no_op"})

            result = worker.execute("lease-live", self.SETUP_PROGRAM, 1)
            self.assertFalse(result.event.error, msg=result.event.result)

            kinds = [event.kind for event in result.events]
            self.assertIn("perturbation_applied", kinds)

            applied = [
                event
                for event in result.events
                if event.kind == "perturbation_applied"
            ]
            by_id = {
                event.payload["perturbation_id"]: event.payload
                for event in applied
            }
            self.assertIn("dis-001-belt", by_id)
            belt_payload = by_id["dis-001-belt"]
            self.assertEqual(belt_payload["status"], "applied")
            belt_destroyed = (
                belt_payload["result"].get("destroyed", {}).get(
                    "transport-belt", 0
                )
            )
            self.assertGreaterEqual(belt_destroyed, 1)
            # The destruction shock knows which product network it hit.
            # (An empty Lua table round-trips as a dict.)
            affected = belt_payload["result"].get("affected_products") or []
            self.assertIsInstance(affected, (list, dict))

            snapshot = worker.finalize("lease-live", task, [result.event])
            summary = snapshot.evidence.get("disruption_summary")
            self.assertIsNotNone(summary)
            # Belt shock applied with effect; depletion may be a no-op on
            # maps without nearby ore, but every scheduled shock resolved.
            self.assertEqual(summary["scheduled"], 2)
            self.assertGreaterEqual(summary["applied"] + summary["no_op"], 2)
            self.assertEqual(summary["pending"], 0)

            snapshot_kinds = {event.kind for event in snapshot.events}
            self.assertIn("perturbation_applied", snapshot_kinds)
        finally:
            worker.release()


if __name__ == "__main__":
    unittest.main()
