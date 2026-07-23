import pytest

from fle.envd.errors import (
    CapacityExhausted,
    InterventionLimitReached,
    LeaseFinalized,
)
from fle.envd.service import EnvironmentService
from tests.envd.conftest import FakeWorker

pytestmark = pytest.mark.no_factorio


def test_lease_execute_finalize_release(task_spec):
    worker = FakeWorker()
    service = EnvironmentService([worker], lease_ttl_seconds=60)

    lease = service.lease(task_spec)
    assert lease.worker_id == worker.worker_id
    assert service.health().available == 0

    first = service.execute(lease.lease_id, "print('one')")
    second = service.execute(lease.lease_id, "print('two')")
    assert first.event.sequence == 1
    assert second.event.sequence == 2
    assert service.observe(lease.lease_id).production_score == 2.0

    snapshot = service.finalize(lease.lease_id)
    assert snapshot.success is True
    assert snapshot.scalar_reward == 2.0
    assert len(snapshot.action_events) == 2
    assert service.finalize(lease.lease_id) == snapshot
    with pytest.raises(LeaseFinalized):
        service.execute(lease.lease_id, "print('too late')")

    assert service.release(lease.lease_id) is True
    assert service.release(lease.lease_id) is False
    assert worker.release_count == 1
    assert service.health().available == 1


def test_capacity_and_intervention_limits(task_spec):
    service = EnvironmentService([FakeWorker()])
    lease = service.lease(task_spec)

    with pytest.raises(CapacityExhausted):
        service.lease(task_spec)

    service.execute(lease.lease_id, "one()")
    service.execute(lease.lease_id, "two()")
    with pytest.raises(InterventionLimitReached):
        service.execute(lease.lease_id, "three()")


def test_terminal_environment_state_blocks_more_actions_but_can_finalize(task_spec):
    class TerminalWorker(FakeWorker):
        def execute(self, lease_id, code, sequence):
            result = super().execute(lease_id, code, sequence)
            result.terminal_reason = "character_died"
            return result

    service = EnvironmentService([TerminalWorker()])
    lease = service.lease(task_spec)

    result = service.execute(lease.lease_id, "walk_across_tracks()")

    assert result.terminal_reason == "character_died"
    with pytest.raises(LeaseFinalized, match="character_died"):
        service.execute(lease.lease_id, "keep_building()")
    snapshot = service.finalize(lease.lease_id)
    assert len(snapshot.action_events) == 1
