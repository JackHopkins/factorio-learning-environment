import pytest

from fle.envd.errors import (
    CapacityExhausted,
    IdempotencyConflict,
    InterventionLimitReached,
    LeaseFinalized,
)
from fle.envd.service import EnvironmentService
from fle.envd.models import FactorioTaskSpec
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


def test_execute_request_id_replays_exact_result_without_mutating(task_spec):
    service = EnvironmentService([FakeWorker()])
    lease = service.lease(task_spec)

    first = service.execute(
        lease.lease_id,
        "print('once')",
        request_id="logical-call-1",
    )
    replay = service.execute(
        lease.lease_id,
        "print('once')",
        request_id="logical-call-1",
    )

    assert replay == first
    assert service.observe(lease.lease_id).production_score == 1.0
    with pytest.raises(IdempotencyConflict):
        service.execute(
            lease.lease_id,
            "print('different')",
            request_id="logical-call-1",
        )


def test_terminal_execute_can_be_replayed_by_request_id(task_spec):
    class TerminalWorker(FakeWorker):
        def execute(self, lease_id, code, sequence):
            result = super().execute(lease_id, code, sequence)
            result.terminal_reason = "contract_fulfilled"
            return result

    service = EnvironmentService([TerminalWorker()])
    lease = service.lease(task_spec)
    first = service.execute(lease.lease_id, "finish()", request_id="finish-1")

    replay = service.execute(lease.lease_id, "finish()", request_id="finish-1")

    assert replay == first
    assert replay.event.sequence == 1


def test_capacity_and_intervention_limits(task_spec):
    service = EnvironmentService([FakeWorker()])
    lease = service.lease(task_spec)

    with pytest.raises(CapacityExhausted):
        service.lease(task_spec)

    service.execute(lease.lease_id, "one()")
    service.execute(lease.lease_id, "two()")
    with pytest.raises(InterventionLimitReached):
        service.execute(lease.lease_id, "three()")


def test_adaptive_contract_tracks_interventions_without_a_hard_limit():
    service = EnvironmentService([FakeWorker()])
    task = FactorioTaskSpec(
        task_id="adaptive-contract",
        goal="Fulfil generated orders.",
        adaptive_contract_session=True,
        max_interventions=2,
    )
    assert task.max_interventions is None
    lease = service.lease(task)

    for index in range(20):
        result = service.execute(lease.lease_id, f"step_{index}()")

    assert result.event.sequence == 20


def test_engine_error_retry_does_not_consume_scored_intervention_budget(task_spec):
    class ErrorWorker(FakeWorker):
        def execute(self, lease_id, code, sequence):
            result = super().execute(lease_id, code, sequence)
            result.event.error = code == "bad()"
            return result

    service = EnvironmentService([ErrorWorker()])
    lease = service.lease(task_spec, tool_error_retry_budget=1)

    rejected = service.execute(lease.lease_id, "bad()")
    first = service.execute(lease.lease_id, "one()")
    second = service.execute(lease.lease_id, "two()")

    assert rejected.event.evaluation_retry is True
    assert first.event.evaluation_retry is False
    assert second.event.sequence == 3
    assert lease.tool_error_retries_used == 1
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


@pytest.mark.parametrize(
    "code",
    [
        "import os",
        "open('host-file.txt', 'w')",
        "instance.rcon_client.send_command('/sc game.speed=1000')",
        "print((1).__class__)",
        "print('{0.__class__}'.format(1))",
        "globals()['escaped'] = True",
        "set_entity_recipe(machine, Prototype.IronGearWheel)",
        "set_entity_recipe(entity=machine, prototype=Prototype.IronGearWheel)",
    ],
)
def test_program_policy_rejects_host_and_namespace_escape(code, task_spec):
    service = EnvironmentService([FakeWorker()])
    lease = service.lease(task_spec)

    result = service.execute(lease.lease_id, code)

    assert result.event.error is True
    assert result.event.sequence == 1
    assert result.event.policy_violations
    assert result.events[0].kind == "invalid_action"
    assert result.events[0].reward_channels == {"invalid_action": -1.0}
    assert service.observe(lease.lease_id).production_score == 0.0
    snapshot = service.finalize(lease.lease_id)
    assert snapshot.action_events[0].policy_violations


def test_program_policy_rejection_uses_tool_retry_budget(task_spec):
    service = EnvironmentService([FakeWorker()])
    lease = service.lease(task_spec, tool_error_retry_budget=1)

    rejected = service.execute(lease.lease_id, "for _ in range(2): pass")
    first = service.execute(lease.lease_id, "one()")
    second = service.execute(lease.lease_id, "two()")

    assert rejected.event.error is True
    assert rejected.event.evaluation_retry is True
    assert first.event.sequence == 2
    assert second.event.sequence == 3
    with pytest.raises(InterventionLimitReached):
        service.execute(lease.lease_id, "three()")


def test_program_policy_allows_normal_factorio_programs(task_spec):
    service = EnvironmentService([FakeWorker()])
    lease = service.lease(task_spec)

    result = service.execute(
        lease.lease_id,
        "from math import ceil\n"
        "for quantity in range(2):\n"
        "    print(ceil(quantity / 2))",
    )

    assert result.event.sequence == 1
