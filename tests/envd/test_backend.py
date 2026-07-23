import pytest

from fle.envd.backend import FLEWorker
from fle.envd.models import FactorioTaskSpec

pytestmark = pytest.mark.no_factorio


def test_live_backend_rejects_unimplemented_world_variants():
    worker = FLEWorker("fake", object())
    task = FactorioTaskSpec(
        task_id="iron_plate_throughput",
        goal="test",
        seed=123,
    )

    with pytest.raises(ValueError, match="pinned default world"):
        worker.start_task(task)
