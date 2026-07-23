"""Verifiers v1 taskset backed by the remote ``factorio-envd`` service.

This module intentionally contains no Factorio process management. Verifiers and
Prime-RL run on Linux and talk over HTTP to a warm environment fleet, which may be
on the same host during development or on separate CPU nodes during training.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any, Literal

import verifiers.v1 as vf
from pydantic import Field

from fle.envd.client import HTTPEnvironmentClient
from fle.envd.benchmark import benchmark_catalog
from fle.envd.curriculum import get_builtin_task
from fle.envd.models import FactorioTaskSpec, VerificationSnapshot
from fle.envd.task_builder import build_task_spec, render_task_prompt

DEFAULT_TASK_IDS = ["iron_plate_throughput"]


class FactorioTaskData(vf.TaskData):
    """Reproducible inputs for one Factorio rollout."""

    task_id: str
    seed: int = 0
    scenario: str = "default_lab_scenario"
    factorio_version: str = "2.0.73"
    checkpoint_id: str = "scenario:default_lab_scenario"
    action_profile: str = "fle-program-v1"
    max_interventions: int = 8
    holdout_seconds: int = 60
    task_spec: FactorioTaskSpec | None = None

    def to_envd_spec(self) -> FactorioTaskSpec:
        if self.task_spec is not None:
            return self.task_spec
        return build_task_spec(
            self.task_id,
            seed=self.seed,
            scenario=self.scenario,
            factorio_version=self.factorio_version,
            checkpoint_id=self.checkpoint_id,
            action_profile=self.action_profile,
            max_interventions=self.max_interventions,
            holdout_seconds=self.holdout_seconds,
        )


class FactorioState(vf.State):
    """Mutable per-rollout state synchronized with the MCP tool server."""

    lease_id: str | None = None
    interventions: int = 0
    last_state_hash: str | None = None
    finalized: bool = False
    terminal_reason: str | None = None


class FactorioToolConfig(vf.ToolsetConfig):
    envd_url: str = "http://127.0.0.1:8172"
    request_timeout_seconds: float = 180.0


class FactorioTools(vf.Toolset[FactorioToolConfig, FactorioState]):
    """Auditable program and observation tools exposed to the policy."""

    TOOL_PREFIX = "factorio"

    def _require_lease(self) -> str:
        if not self.state.lease_id:
            raise RuntimeError("Factorio rollout has no active environment lease")
        return self.state.lease_id

    @vf.tool
    async def execute_program(self, code: str) -> dict[str, Any]:
        """Execute one short Python intervention through FLE's auditable program API."""
        lease_id = self._require_lease()
        async with HTTPEnvironmentClient(
            self.config.envd_url, self.config.request_timeout_seconds
        ) as client:
            result = await client.execute(lease_id, code)
        self.state.interventions = result.event.sequence
        self.state.last_state_hash = result.state_hash
        self.state.terminal_reason = result.terminal_reason
        return result.model_dump(mode="json")

    @vf.tool
    async def observe_factory(self) -> dict[str, Any]:
        """Inspect current inventory, production statistics, ticks, and state hash."""
        lease_id = self._require_lease()
        async with HTTPEnvironmentClient(
            self.config.envd_url, self.config.request_timeout_seconds
        ) as client:
            observation = await client.observe(lease_id)
        self.state.last_state_hash = observation.state_hash
        return observation.model_dump(mode="json")


class FactorioTaskConfig(vf.TaskConfig):
    tools: FactorioToolConfig = FactorioToolConfig()


class FactorioTask(vf.Task[FactorioTaskData, FactorioState, FactorioTaskConfig]):
    """One Verifiers rollout whose authority remains the Factorio engine."""

    tools = (FactorioTools,)

    async def setup(self, trace: vf.Trace, runtime: vf.Runtime) -> None:
        async with HTTPEnvironmentClient(
            self.config.tools.envd_url,
            self.config.tools.request_timeout_seconds,
        ) as client:
            lease = await client.lease(self.data.to_envd_spec())
        trace.state.lease_id = lease.lease_id
        trace.state.last_state_hash = lease.initial_state_hash
        trace.info["factorio_task_fingerprint"] = lease.task.fingerprint
        trace.info["factorio_worker_id"] = lease.worker_id

    async def finalize(self, trace: vf.Trace, runtime: vf.Runtime) -> None:
        lease_id = trace.state.lease_id
        if not lease_id:
            return
        async with HTTPEnvironmentClient(
            self.config.tools.envd_url,
            self.config.tools.request_timeout_seconds,
        ) as client:
            try:
                snapshot = await client.finalize(lease_id)
                trace.info["factorio_verification"] = snapshot.model_dump(mode="json")
                if snapshot.privileged_diagnostics is not None:
                    trace.info["factorio_privileged_teacher"] = (
                        snapshot.privileged_diagnostics.model_dump(mode="json")
                    )
                trace.state.last_state_hash = snapshot.terminal_state_hash
                trace.state.terminal_reason = snapshot.termination_reason
                trace.state.finalized = True
            finally:
                await client.release(lease_id)
                trace.state.lease_id = None

    def _snapshot(self, trace: vf.Trace) -> VerificationSnapshot | None:
        payload = trace.info.get("factorio_verification")
        return VerificationSnapshot.model_validate(payload) if payload else None

    @vf.stop
    async def intervention_limit(self, trace: vf.Trace) -> bool:
        return trace.state.interventions >= self.data.max_interventions

    @vf.stop
    async def terminal_environment_state(self, trace: vf.Trace) -> bool:
        return trace.state.terminal_reason is not None

    @vf.reward
    async def factorio_reward(self, trace: vf.Trace) -> float:
        snapshot = self._snapshot(trace)
        return snapshot.scalar_reward if snapshot else 0.0

    @vf.metric
    async def factorio_metrics(self, trace: vf.Trace) -> dict[str, float]:
        snapshot = self._snapshot(trace)
        if snapshot is None:
            return {
                "factorio_success": 0.0,
                "factorio_interventions": float(trace.state.interventions),
            }
        return {
            "factorio_success": float(snapshot.success),
            "factorio_interventions": float(len(snapshot.action_events)),
            "factorio_task_reward": snapshot.rewards.task,
            "factorio_throughput": snapshot.rewards.throughput,
            "factorio_automation": snapshot.rewards.automation,
            "factorio_progress": snapshot.rewards.progress,
            "factorio_invalid_action": snapshot.rewards.invalid_action,
            "factorio_milestone": snapshot.rewards.milestone,
            "factorio_robustness": snapshot.rewards.robustness,
            "factorio_time_efficiency": snapshot.rewards.time_efficiency,
            "factorio_manual_intervention": snapshot.rewards.manual_intervention,
            "factorio_resource_cost": snapshot.rewards.resource_cost,
        }


class FactorioTasksetConfig(vf.TasksetConfig):
    task_ids: list[str] = DEFAULT_TASK_IDS
    builtin_task_ids: list[str] = Field(default_factory=list)
    benchmark_suites: list[str] = Field(default_factory=list)
    benchmark_statuses: list[
        Literal["ready", "calibration_required", "spec_only", "planned"]
    ] = Field(default_factory=lambda: ["ready"])
    task_specs: list[FactorioTaskSpec] = Field(default_factory=list)
    seed: int = 0
    scenario: str = "default_lab_scenario"
    factorio_version: str = "2.0.73"
    checkpoint_id: str = "scenario:default_lab_scenario"
    action_profile: str = "fle-program-v1"
    max_interventions: int = 8
    holdout_seconds: int = 60
    task: FactorioTaskConfig = FactorioTaskConfig()


class FactorioTaskset(vf.Taskset[FactorioTask, FactorioTasksetConfig]):
    """Finite curriculum slice selected from any supported FLE registry task."""

    def load(self) -> Iterator[FactorioTask]:
        config = self.config
        specs = list(config.task_specs)
        specs.extend(get_builtin_task(task_id) for task_id in config.builtin_task_ids)
        requested_suites = set(config.benchmark_suites)
        requested_statuses = set(config.benchmark_statuses)
        catalog = benchmark_catalog()
        benchmark_specs = [
            item.task_spec
            for item in catalog
            if item.suite in requested_suites and item.status in requested_statuses
        ]
        if requested_suites and not benchmark_specs:
            known_suites = ", ".join(sorted({item.suite for item in catalog}))
            raise ValueError(
                "Benchmark selection matched no tasks; "
                f"known suites: {known_suites}"
            )
        specs.extend(benchmark_specs)
        specs = list({spec.task_id: spec for spec in specs}.values())
        if not specs:
            specs = [
                build_task_spec(
                    task_id,
                    seed=config.seed + idx,
                    scenario=config.scenario,
                    factorio_version=config.factorio_version,
                    checkpoint_id=config.checkpoint_id,
                    action_profile=config.action_profile,
                    max_interventions=config.max_interventions,
                    holdout_seconds=config.holdout_seconds,
                )
                for idx, task_id in enumerate(config.task_ids)
            ]
        for idx, spec in enumerate(specs):
            task_id = spec.task_id
            goal = spec.goal
            prompt = render_task_prompt(spec)
            yield FactorioTask(
                FactorioTaskData(
                    idx=idx,
                    name=f"{task_id}#{config.seed + idx}",
                    description=goal,
                    prompt=prompt,
                    task_id=task_id,
                    seed=spec.seed,
                    scenario=spec.scenario,
                    factorio_version=spec.factorio_version,
                    checkpoint_id=spec.checkpoint_id,
                    action_profile=spec.action_profile,
                    max_interventions=spec.max_interventions,
                    holdout_seconds=spec.holdout_seconds,
                    task_spec=spec,
                ),
                config.task,
            )


if __name__ == "__main__":
    FactorioTools.run()
