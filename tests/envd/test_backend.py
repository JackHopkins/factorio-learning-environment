import pytest

from fle.envd.backend import FLEWorker
from fle.envd.models import FactorioTaskSpec

pytestmark = pytest.mark.no_factorio


def test_worker_accepts_declared_seeds(tmp_path, monkeypatch):
    """Seeds are a container-launch concern: workers accept any value."""

    monkeypatch.setenv("FLE_LIFECYCLE_DIR", str(tmp_path / "lifecycle"))
    worker = FLEWorker("fake", object())
    task = FactorioTaskSpec(
        task_id="iron_plate_throughput",
        goal="test",
        seed=123,
        checkpoint_id="scenario:default_lab_scenario",
    )
    # Validation passes; the fake instance cannot actually reset.
    with pytest.raises(AttributeError):
        worker.start_task(task)


def test_worker_rejects_unknown_checkpoint_namespace(tmp_path, monkeypatch):
    monkeypatch.setenv("FLE_LIFECYCLE_DIR", str(tmp_path / "lifecycle"))
    worker = FLEWorker("fake", object())
    task = FactorioTaskSpec(
        task_id="t",
        goal="test",
        checkpoint_id="weird:thing",
    )
    with pytest.raises(ValueError, match="pinned default world"):
        worker.start_task(task)


def test_worker_rejects_missing_lifecycle_checkpoint(tmp_path, monkeypatch):
    monkeypatch.setenv("FLE_LIFECYCLE_DIR", str(tmp_path / "lifecycle"))
    worker = FLEWorker("fake", object())
    task = FactorioTaskSpec(
        task_id="t",
        goal="test",
        checkpoint_id="lifecycle:map-0001:ep1",
    )
    with pytest.raises(ValueError, match="not found"):
        worker.start_task(task)
