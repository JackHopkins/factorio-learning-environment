from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from fle.commons.constants import REWARD_OVERRIDE_KEY
from fle.commons.models.game_state import GameState
from fle.env import FactorioInstance
from fle.envd.models import (
    ActionEvent,
    ExecutionResult,
    FactorioTaskSpec,
    Observation,
    RewardVector,
    VerifierEvent,
    VerificationSnapshot,
    canonical_hash,
)
from fle.envd.objective_engine import (
    TelemetryFrame,
    _objective_telemetry,
    _sequence,
    capture_telemetry,
    verify_native,
)
from fle.eval.tasks import TaskFactory


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump())
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if hasattr(value, "__dict__"):
        return _jsonable(vars(value))
    return str(value)


def _instance_state_hash(instance: FactorioInstance) -> str:
    raw = GameState.from_instance(instance).to_raw()
    state = __import__("json").loads(raw)
    state.pop("timestamp", None)
    return canonical_hash(state)


class FactorioWorker(ABC):
    """One exclusively leased Factorio simulation worker."""

    worker_id: str

    @abstractmethod
    def start_task(self, task: FactorioTaskSpec) -> str:
        """Reset and provision the task, returning its initial state hash."""

    @abstractmethod
    def execute(self, lease_id: str, code: str, sequence: int) -> ExecutionResult:
        pass

    @abstractmethod
    def observe(self, lease_id: str) -> Observation:
        pass

    @abstractmethod
    def finalize(
        self, lease_id: str, task: FactorioTaskSpec, events: list[ActionEvent]
    ) -> VerificationSnapshot:
        pass

    @abstractmethod
    def release(self) -> None:
        pass


class FLEWorker(FactorioWorker):
    """Factorio worker backed by an existing FLE RCON instance."""

    def __init__(self, worker_id: str, instance: FactorioInstance):
        self.worker_id = worker_id
        self.instance = instance
        self.task = None
        self.task_spec: FactorioTaskSpec | None = None
        self.initial_telemetry: TelemetryFrame | None = None
        self._executed_tools_current: list[str] = []
        self._capture_tool_calls = False
        for tool_name in getattr(self.instance, "controllers", {}):

            def record_tool(_tool, *_args, _name=tool_name, **_kwargs):
                if self._capture_tool_calls:
                    self._executed_tools_current.append(_name)

            self.instance.pre_tool_hooks.setdefault(tool_name, []).append(record_tool)

    @classmethod
    def connect(
        cls,
        worker_id: str,
        tcp_port: int,
        address: str = "localhost",
    ) -> "FLEWorker":
        instance = FactorioInstance(
            address=address,
            tcp_port=tcp_port,
            fast=True,
            cache_scripts=True,
            inventory={},
            all_technologies_researched=False,
            clear_entities=False,
        )
        return cls(worker_id, instance)

    def start_task(self, task: FactorioTaskSpec) -> str:
        supported = {
            "scenario": "default_lab_scenario",
            "factorio_version": "2.0.73",
            "checkpoint_id": "scenario:default_lab_scenario",
            "action_profile": "fle-program-v1",
            "seed": 0,
        }
        requested = {
            "scenario": task.scenario,
            "factorio_version": task.factorio_version,
            "checkpoint_id": task.checkpoint_id,
            "action_profile": task.action_profile,
            "seed": task.seed,
        }
        unsupported = {
            key: {"requested": requested[key], "supported": expected}
            for key, expected in supported.items()
            if requested[key] != expected
        }
        if unsupported:
            raise ValueError(
                "The first envd backend only supports the pinned default world: "
                f"{unsupported}"
            )
        fle_task = TaskFactory.create_task(task.backend_task_id or task.task_id)
        if hasattr(fle_task, "holdout_wait_period"):
            fle_task.holdout_wait_period = task.holdout_seconds
        provisioning = task.provisioning
        self.instance.initial_inventory = (
            provisioning.starting_inventory
            if provisioning.starting_inventory is not None
            else fle_task.starting_inventory
        )
        all_research = (
            provisioning.all_technologies_researched
            if provisioning.all_technologies_researched is not None
            else fle_task.all_technology_reserached
        )
        # Independent benchmark leases must not inherit the previous agent's
        # location.  Reach-limited actions otherwise become task-order
        # dependent after any rollout that moves the character.
        self.instance.reset(
            reset_position=True,
            all_technologies_researched=all_research,
        )
        fle_task.setup_instance(self.instance)
        self.instance.rcon_client.send_command(
            "/sc game.forces.player.character_inventory_slots_bonus = "
            f"{provisioning.character_inventory_slots_bonus}"
        )
        if provisioning.starting_inventory is not None:
            self.instance.first_namespace._set_inventory(
                provisioning.starting_inventory
            )
        for technology in provisioning.researched_technologies:
            technology_name = json.dumps(technology)
            self.instance.rcon_client.send_command(
                "/sc local technology = "
                f"game.forces.player.technologies[{technology_name}]; "
                "if technology then technology.researched = true end"
            )
        self.instance._verified_rocket_launches = 0
        _objective_telemetry(self.instance.first_namespace, reset=True)
        self.instance.set_speed(10)
        self.instance.pause()
        self.task = fle_task
        self.task_spec = task
        targets = [
            objective.target for objective in task.objectives if objective.target
        ]
        self.initial_telemetry = capture_telemetry(self.instance, targets)
        return _instance_state_hash(self.instance)

    def _scores(self) -> tuple[float, float]:
        production, automated = self.instance.first_namespace.score()
        return float(production or 0), float(automated or 0)

    def execute(self, lease_id: str, code: str, sequence: int) -> ExecutionResult:
        before, _ = self._scores()
        started = datetime.now(timezone.utc)
        self._executed_tools_current = []
        self._capture_tool_calls = True
        self.instance.set_speed_and_unpause(10)
        try:
            _, duration, result = self.instance.eval(code, timeout=120)
        finally:
            self._capture_tool_calls = False
            # Model generation and network latency must not advance simulation time.
            self.instance.pause()
        after, automated = self._scores()
        result_text = str(result)
        error = "error" in result_text.lower() or "exception:" in result_text.lower()
        forbidden_actions = {
            str(action)
            for constraint in (self.task_spec.constraints if self.task_spec else [])
            if constraint.kind == "forbidden_action"
            for action in constraint.parameters.get(
                "actions",
                [constraint.limit] if constraint.limit is not None else [],
            )
        }
        executed_tools = list(self._executed_tools_current)
        # FactorioNamespace.eval_with_timeout always calls score() after the
        # submitted program. That verifier-internal call is not a policy action.
        if executed_tools and executed_tools[-1] == "score":
            executed_tools.pop()
        policy_violations = [
            tool for tool in executed_tools if tool in forbidden_actions
        ]
        lifecycle = _objective_telemetry(self.instance.first_namespace)
        character_died = int(lifecycle.get("death_count", 0) or 0) > 0
        terminal_reason = "character_died" if character_died else None
        event = ActionEvent(
            sequence=sequence,
            code_sha256=hashlib.sha256(code.encode()).hexdigest(),
            started_at=started,
            duration_seconds=duration,
            reward_delta=after - before,
            error=error,
            result=result_text,
            ticks=self.instance.get_elapsed_ticks(),
            executed_tools=executed_tools,
            policy_violations=policy_violations,
        )
        verifier_event = VerifierEvent(
            event_id=f"action:{sequence}",
            kind="invalid_action" if error else "intervention_executed",
            tick=event.ticks,
            source="environment",
            payload={
                "sequence": sequence,
                "code_sha256": event.code_sha256,
                "duration_seconds": duration,
                "executed_tools": executed_tools,
                "policy_violations": policy_violations,
            },
            evidence={"result": result_text} if error else {},
            reward_channels={"invalid_action": -1.0} if error else {},
        )
        emitted_events = [verifier_event]
        if character_died:
            deaths = _sequence(lifecycle.get("deaths"))
            latest_death = deaths[-1] if deaths else {}
            emitted_events.append(
                VerifierEvent(
                    event_id=f"lifecycle:death:action:{sequence}",
                    kind="character_died",
                    tick=int(latest_death.get("tick", event.ticks)),
                    source="engine",
                    payload={
                        "sequence": sequence,
                        "train_involved": latest_death.get("train") is not None,
                    },
                    evidence=latest_death,
                )
            )
        return ExecutionResult(
            lease_id=lease_id,
            event=event,
            production_score=after,
            automated_production_score=automated,
            state_hash=_instance_state_hash(self.instance),
            events=emitted_events,
            terminal_reason=terminal_reason,
        )

    def observe(self, lease_id: str) -> Observation:
        production, automated = self._scores()
        namespace = self.instance.first_namespace
        inventory = _jsonable(namespace.inspect_inventory())
        stats = _jsonable(namespace._get_production_stats())
        return Observation(
            lease_id=lease_id,
            task_id=self.task_spec.task_id if self.task_spec else "unknown",
            ticks=self.instance.get_elapsed_ticks(),
            inventory=inventory,
            production_score=production,
            automated_production_score=automated,
            production=stats,
            state_hash=_instance_state_hash(self.instance),
        )

    def finalize(
        self, lease_id: str, task: FactorioTaskSpec, events: list[ActionEvent]
    ) -> VerificationSnapshot:
        if self.task is None:
            raise RuntimeError("Worker has no active task")

        production, automated = self._scores()
        if task.verifier.implementation == "objective_engine_v1":
            if self.initial_telemetry is None:
                raise RuntimeError("Native verifier has no initial telemetry")
            self.instance.set_speed_and_unpause(10)
            try:
                native = verify_native(
                    self.instance,
                    task,
                    events,
                    self.initial_telemetry,
                )
            finally:
                self.instance.pause()
            return VerificationSnapshot(
                lease_id=lease_id,
                task_id=task.task_id,
                task_fingerprint=task.fingerprint,
                success=native.success,
                scalar_reward=native.scalar_reward,
                rewards=native.rewards,
                metrics=native.metrics,
                evidence={
                    "verifier": "objective_engine_v1",
                    "task_family": task.task_family,
                    "backend_task_id": task.backend_task_id or task.task_id,
                    "objective_ids": [
                        objective.objective_id for objective in task.objectives
                    ],
                    "scalarization": task.verifier.scalarization,
                },
                terminal_state_hash=_instance_state_hash(self.instance),
                action_events=events,
                events=[
                    *[
                        VerifierEvent(
                            event_id=f"action:{event.sequence}",
                            kind=(
                                "invalid_action"
                                if event.error
                                else "intervention_executed"
                            ),
                            tick=event.ticks,
                            source="environment",
                            payload={
                                "sequence": event.sequence,
                                "code_sha256": event.code_sha256,
                            },
                            reward_channels=(
                                {"invalid_action": -1.0} if event.error else {}
                            ),
                        )
                        for event in events
                    ],
                    *native.events,
                ],
                termination_reason=native.termination_reason,
                privileged_diagnostics=native.diagnostics,
            )

        self.instance.set_speed_and_unpause(10)
        try:
            response = self.task.verify(production, self.instance, step_statistics={})
        finally:
            self.instance.pause()
        metrics = _jsonable(response.meta)
        scalar = float(metrics.get(REWARD_OVERRIDE_KEY, float(response.success)))
        throughput = max(
            (
                float(value)
                for key, value in metrics.items()
                if "throughput" in str(key).lower() and isinstance(value, (int, float))
            ),
            default=0.0,
        )
        invalid = -float(sum(event.error for event in events))
        primary_objective = task.objectives[0] if task.objectives else None
        verification_event = VerifierEvent(
            event_id="verification:final",
            kind="objective_satisfied" if response.success else "objective_failed",
            tick=self.instance.get_elapsed_ticks(),
            source="verifier",
            objective_id=(
                primary_objective.objective_id if primary_objective else None
            ),
            payload={
                "success": bool(response.success),
                "scalar_reward": scalar,
                "task_family": task.task_family,
            },
            evidence={"metrics": metrics},
            reward_channels={
                "task": float(response.success),
                "throughput": throughput,
            },
        )
        return VerificationSnapshot(
            lease_id=lease_id,
            task_id=task.task_id,
            task_fingerprint=task.fingerprint,
            success=bool(response.success),
            scalar_reward=scalar,
            rewards=RewardVector(
                task=float(response.success),
                throughput=throughput,
                automation=max(automated, 0.0),
                progress=production,
                invalid_action=invalid,
            ),
            metrics={
                **metrics,
                "production_score": production,
                "automated_production_score": automated,
                "automation_reward": max(automated, 0.0),
                "automation_reward_basis": "nonnegative_legacy_net_value_delta",
                "interventions": len(events),
                "scored_interventions": sum(
                    not event.evaluation_retry for event in events
                ),
                "evaluation_retries": sum(event.evaluation_retry for event in events),
            },
            evidence={
                "verifier": type(self.task).__name__,
                "task_family": task.task_family,
                "backend_task_id": task.backend_task_id or task.task_id,
                "objective_ids": [
                    objective.objective_id for objective in task.objectives
                ],
                "scalarization": task.verifier.scalarization,
            },
            terminal_state_hash=_instance_state_hash(self.instance),
            action_events=events,
            events=[
                *[
                    VerifierEvent(
                        event_id=f"action:{event.sequence}",
                        kind=(
                            "invalid_action" if event.error else "intervention_executed"
                        ),
                        tick=event.ticks,
                        source="environment",
                        payload={
                            "sequence": event.sequence,
                            "code_sha256": event.code_sha256,
                            "evaluation_retry": event.evaluation_retry,
                        },
                        reward_channels=(
                            {"invalid_action": -1.0} if event.error else {}
                        ),
                    )
                    for event in events
                ],
                verification_event,
                VerifierEvent(
                    event_id="verification:completed",
                    kind="verification_completed",
                    tick=self.instance.get_elapsed_ticks(),
                    source="verifier",
                    payload={"success": bool(response.success)},
                ),
            ],
            termination_reason=(
                "success"
                if response.success
                else (
                    "character_died"
                    if int(
                        _objective_telemetry(self.instance.first_namespace).get(
                            "death_count", 0
                        )
                        or 0
                    )
                    else "finalized"
                )
            ),
        )

    def release(self) -> None:
        self.instance.pause()
        self.task = None
        self.task_spec = None
        self.initial_telemetry = None
