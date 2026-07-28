import sys
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

if sys.platform == "win32":
    pytest.skip(
        "Verifiers v1 uses Unix process primitives; test the adapter on Linux",
        allow_module_level=True,
    )

from fle.envd.models import (  # noqa: E402
    ActionEvent,
    ExecutionResult,
    Lease,
    ObjectiveSpec,
    FactorioTaskSpec,
    PrivilegedDiagnosticPacket,
    RewardVector,
    VerificationSnapshot,
)
from fle.integrations.prime_v1 import taskset as prime_taskset  # noqa: E402
from verifiers.v1.loaders import taskset_class  # noqa: E402

pytestmark = [pytest.mark.no_factorio]


class FakeClient:
    released: list[str] = []

    def __init__(self, base_url: str, timeout_seconds: float):
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    async def lease(self, spec):
        now = datetime.now(timezone.utc)
        return Lease(
            lease_id="lease-1",
            worker_id="worker-0",
            task=spec,
            initial_state_hash="initial-hash",
            created_at=now,
            expires_at=now + timedelta(minutes=5),
        )

    async def execute(self, lease_id: str, code: str):
        return ExecutionResult(
            lease_id=lease_id,
            event=ActionEvent(
                sequence=1,
                code_sha256="a" * 64,
                started_at=datetime.now(timezone.utc),
                duration_seconds=0.1,
                result=code,
            ),
            production_score=2.0,
            automated_production_score=1.0,
            state_hash="action-hash",
        )

    async def finalize(self, lease_id: str):
        return VerificationSnapshot(
            lease_id=lease_id,
            task_id="iron_plate_throughput",
            task_fingerprint="task-hash",
            success=True,
            scalar_reward=1.25,
            rewards=RewardVector(task=1.0, throughput=16.0, progress=2.0),
            terminal_state_hash="terminal-hash",
            action_events=[],
            privileged_diagnostics=PrivilegedDiagnosticPacket(
                task_id="iron_plate_throughput",
                tick=60,
                elapsed_ticks=60,
            ),
        )

    async def release(self, lease_id: str):
        self.released.append(lease_id)


def test_taskset_loads_reproducible_throughput_task():
    config = prime_taskset.FactorioTasksetConfig(
        task_ids=["iron_plate_throughput"], seed=41
    )
    task = prime_taskset.FactorioTaskset(config).select()[0]

    assert task.data.task_id == "iron_plate_throughput"
    assert task.data.seed == 41
    spec = task.data.to_envd_spec()
    assert spec.fingerprint
    assert spec.task_family == "throughput"
    assert spec.objectives[0].kind == "throughput"
    assert "engine and task verifier determine success" in task.data.prompt_text
    assert "get_prototype_recipe" in task.data.prompt_text
    assert "no host/file/network access" in task.data.prompt_text
    assert task.config.tools.envd_url == "http://127.0.0.1:8172"


def test_verifiers_loader_discovers_local_taskset():
    assert taskset_class("factorio_v1") is prime_taskset.FactorioTaskset


def test_taskset_accepts_explicit_non_throughput_task_contract():
    spec = FactorioTaskSpec(
        task_id="bootstrap-automation",
        backend_task_id="open_play",
        goal="Research automation.",
        task_family="progression",
        objectives=[
            ObjectiveSpec(
                objective_id="research-automation",
                kind="research",
                description="Research automation.",
                target="automation",
                comparator="eq",
                threshold=1,
            )
        ],
    )
    task = prime_taskset.FactorioTaskset(
        prime_taskset.FactorioTasksetConfig(task_specs=[spec])
    ).select()[0]

    assert task.data.to_envd_spec() == spec
    assert task.data.to_envd_spec().task_family == "progression"
    assert "Research automation" in task.data.prompt_text


def test_taskset_loads_builtin_progression_curriculum_by_id():
    task = prime_taskset.FactorioTaskset(
        prime_taskset.FactorioTasksetConfig(
            builtin_task_ids=["progression_early_automation_v1"]
        )
    ).select()[0]

    spec = task.data.to_envd_spec()
    assert spec.task_id == "progression_early_automation_v1"
    assert spec.verifier.implementation == "objective_engine_v1"
    assert spec.curriculum.episode_mode == "persistent"
    assert task.data.max_interventions == 64


def test_taskset_selects_ready_benchmark_suite_without_manual_id_list():
    tasks = prime_taskset.FactorioTaskset(
        prime_taskset.FactorioTasksetConfig(
            benchmark_suites=["robustness_v1"],
            benchmark_statuses=["ready"],
        )
    ).select()

    task_ids = {task.data.task_id for task in tasks}
    assert task_ids == {
        "robustness_circuit_no_manual_v1",
        "robustness_productive_survival_v1",
    }


def test_taskset_selects_microtask_calibration_suite():
    tasks = prime_taskset.FactorioTaskset(
        prime_taskset.FactorioTasksetConfig(
            benchmark_suites=["api_microtasks_v1"],
            benchmark_statuses=["calibration_required"],
        )
    ).select()

    assert len(tasks) == 3
    assert all(task.data.max_interventions <= 6 for task in tasks)
    assert all(
        task.data.task_spec.verifier.implementation == "objective_engine_v1"
        for task in tasks
    )


def test_unknown_benchmark_suite_fails_instead_of_loading_default_task():
    taskset = prime_taskset.FactorioTaskset(
        prime_taskset.FactorioTasksetConfig(
            benchmark_suites=["not_a_real_suite"],
        )
    )

    with pytest.raises(ValueError, match="known suites"):
        taskset.select()


def test_prime_smoke_environment_config_resolves():
    path = Path(__file__).parents[2] / "integrations" / "prime" / "rl-smoke.toml"
    with path.open("rb") as handle:
        config = tomllib.load(handle)

    raw_environment = config["orchestrator"]["train"]["env"][0]
    environment = {key: raw_environment[key] for key in ("taskset", "harness")}
    resolved = prime_taskset.vf.EnvConfig.model_validate(environment)
    assert isinstance(resolved.taskset, prime_taskset.FactorioTasksetConfig)
    assert resolved.taskset.task.tools.envd_url == "http://127.0.0.1:8172"


@pytest.mark.asyncio
async def test_task_lifecycle_persists_verification_and_releases(monkeypatch):
    monkeypatch.setattr(prime_taskset, "HTTPEnvironmentClient", FakeClient)
    FakeClient.released.clear()
    task = prime_taskset.FactorioTaskset(
        prime_taskset.FactorioTasksetConfig()
    ).select()[0]
    trace = SimpleNamespace(state=prime_taskset.FactorioState(), info={})

    await task.setup(trace, None)
    assert trace.state.lease_id == "lease-1"
    assert trace.state.last_state_hash == "initial-hash"

    tools = prime_taskset.FactorioTools(task.config.tools)
    tools._inert_state = trace.state
    result = await tools.execute_program("print('hello')")
    assert result["state_hash"] == "action-hash"
    assert trace.state.interventions == 1

    await task.finalize(trace, None)
    assert trace.state.finalized is True
    assert trace.state.lease_id is None
    assert FakeClient.released == ["lease-1"]
    assert trace.info["factorio_privileged_teacher"]["task_id"] == (
        "iron_plate_throughput"
    )
    assert await task.factorio_reward(trace) == 1.25
    metrics = await task.factorio_metrics(trace)
    assert metrics["factorio_success"] == 1.0
    assert metrics["factorio_throughput"] == 16.0
