import unittest

from fle.envd.backend import FLEWorker
from fle.envd.models import (
    CustomerContractSpec,
    DemandOrderSpec,
    FactorioTaskSpec,
    ProductDemandSpec,
    VerifierSpec,
)

TICKS_PER_HOUR = 216000


class TestCustomerContractsLive(unittest.TestCase):
    """End-to-end contract fulfillment against a live Factorio server."""

    def _worker(self) -> FLEWorker:
        return FLEWorker.connect("live-customer-worker", tcp_port=27000)

    def _task_spec(self) -> FactorioTaskSpec:
        immediate = DemandOrderSpec(
            order_id="ord-001-bulk",
            kind="one_shot",
            products=[ProductDemandSpec(product="iron-plate", quantity=50.0)],
            issue_tick=0,
            due_tick=TICKS_PER_HOUR,
        )
        future = DemandOrderSpec(
            order_id="ord-002-future",
            kind="one_shot",
            products=[ProductDemandSpec(product="copper-plate", quantity=20.0)],
            issue_tick=TICKS_PER_HOUR * 2,
            due_tick=TICKS_PER_HOUR * 3,
        )
        return FactorioTaskSpec(
            task_id="customer_contract_live_v1",
            goal="Fulfill customer orders by delivering items to the depot.",
            verifier=VerifierSpec(implementation="objective_engine_v1"),
            customer=CustomerContractSpec(
                orders=[immediate, future],
                depot_chests=4,
                lateness_penalty_weight=0.25,
                success_ratio=1.0,
            ),
            provisioning={"starting_inventory": {"iron-plate": 100}},
            max_interventions=8,
            holdout_seconds=1,
        )

    DELIVER_PROGRAM = """
depot = get_entities({Prototype.SteelChest})[0]
move_to(depot.position)
insert_item(Prototype.IronPlate, depot, quantity=50)
sleep(1)
print('delivered')
"""

    def test_end_to_end_fulfillment(self):
        worker = self._worker()
        task = self._task_spec()

        try:
            initial_hash = worker.start_task(task)
            self.assertTrue(initial_hash)

            # Only the issued order is visible; future demand stays hidden.
            before = worker.observe("lease-live")
            self.assertEqual(len(before.contracts), 1)
            self.assertEqual(before.contracts[0].order_id, "ord-001-bulk")
            self.assertEqual(before.contracts[0].status, "open")
            self.assertEqual(before.contracts[0].fulfilled.get("iron-plate"), 0.0)

            result = worker.execute("lease-live", self.DELIVER_PROGRAM, 1)
            self.assertFalse(result.event.error, msg=result.event.result)

            after = worker.observe("lease-live")
            self.assertEqual(len(after.contracts), 1)
            self.assertEqual(
                after.contracts[0].fulfilled.get("iron-plate"), 50.0
            )

            snapshot = worker.finalize("lease-live", task, [result.event])
            self.assertTrue(snapshot.success, msg=str(snapshot.metrics)[:2000])
            self.assertIn("customer_commitment", snapshot.evidence)
            self.assertEqual(snapshot.metrics["customer_aggregate_ratio"], 1.0)
            self.assertGreater(len(snapshot.metrics["customer_receipt_mac"]), 0)

            kinds = {event.kind for event in snapshot.events}
            self.assertIn("contract_issued", kinds)
            self.assertIn("contract_fulfilled", kinds)

            contract_objectives = [
                evaluation
                for evaluation in snapshot.metrics["objective_evaluations"]
                if evaluation["objective_id"] == "customer:contracts"
            ]
            self.assertEqual(len(contract_objectives), 1)
            self.assertTrue(contract_objectives[0]["satisfied"])
            self.assertIsNotNone(contract_objectives[0]["evidence"]["receipt_mac"])
        finally:
            worker.release()


if __name__ == "__main__":
    unittest.main()
