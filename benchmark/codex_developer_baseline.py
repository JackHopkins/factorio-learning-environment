"""Reproduce the first non-blind Codex developer baseline.

This is deliberately not presented as an API-sampled model baseline. The
programs were authored by GPT-5.6-Sol while operating the development
environment and are retained so the first engine run remains reproducible and
auditable.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fle.envd.benchmark import benchmark_catalog
from fle.envd.benchmark_results import (
    BenchmarkAttempt,
    BenchmarkRun,
    ModelIdentity,
    summarize_run,
    validate_against_catalog,
)
from fle.envd.client import EnvironmentClientError, HTTPEnvironmentClient
from fle.envd.models import VerificationSnapshot
from fle.envd.task_builder import render_task_prompt

PROGRAMS: dict[str, list[str]] = {
    "micro_configure_assembler_recipe_v1": [
        """\
a = place_entity(Prototype.AssemblingMachine1, position=Position(x=0, y=0))
a = set_entity_recipe(a, Prototype.IronGearWheel)
print(a)
"""
    ],
    "micro_craft_iron_gear_v1": [
        """\
print(craft_item(Prototype.IronGearWheel, 1))
print(inspect_inventory())
"""
    ],
    "micro_fuel_furnace_v1": [
        """\
f = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
f = insert_item(Prototype.Coal, f, 1)
print(inspect_inventory(f))
"""
    ],
    "micro_harvest_coal_v1": [
        """\
p = nearest(Resource.Coal)
move_to(p)
print(harvest_resource(p, 5))
print(inspect_inventory())
"""
    ],
    "micro_load_lab_v1": [
        """\
lab = place_entity(Prototype.Lab, position=Position(x=0, y=0))
lab = insert_item(Prototype.AutomationSciencePack, lab, 5)
print(inspect_inventory(lab))
"""
    ],
    "micro_place_entity_next_to_v1": [
        """\
lab = place_entity(Prototype.Lab, position=Position(x=0, y=0))
pole = place_entity_next_to(
    Prototype.SmallElectricPole,
    lab.position,
    Direction.RIGHT,
)
print(lab, pole)
"""
    ],
    "micro_place_lab_v1": [
        """\
print(place_entity(Prototype.Lab, position=Position(x=0, y=0)))
"""
    ],
    "micro_transfer_to_chest_v1": [
        """\
chest = place_entity(Prototype.WoodenChest, position=Position(x=0, y=0))
chest = insert_item(Prototype.IronPlate, chest, 10)
print(inspect_inventory(chest))
"""
    ],
    "micro_automate_iron_gear_v1": [
        """\
solar = place_entity(Prototype.SolarPanel, position=Position(x=-6, y=0))
assembler = place_entity(
    Prototype.AssemblingMachine1,
    position=Position(x=0, y=0),
)
assembler = set_entity_recipe(assembler, Prototype.IronGearWheel)
assembler = insert_item(Prototype.IronPlate, assembler, 10)
print(connect_entities(solar, assembler, Prototype.SmallElectricPole))
sleep(5)
print(get_entity(Prototype.AssemblingMachine1, assembler.position))
"""
    ],
    "micro_automate_steel_plate_v1": [
        """\
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
furnace = insert_item(Prototype.IronPlate, furnace, 10)
furnace = insert_item(Prototype.Coal, furnace, 10)
sleep(15)
sleep(5)
print(inspect_inventory(furnace))
"""
    ],
    "micro_start_furnace_v1": [
        """\
furnace = place_entity(Prototype.StoneFurnace, position=Position(x=0, y=0))
furnace = insert_item(Prototype.IronOre, furnace, 5)
furnace = insert_item(Prototype.Coal, furnace, 5)
sleep(2)
print(furnace)
"""
    ],
    "micro_automate_electronic_circuit_v1": [
        """\
solar = place_entity(Prototype.SolarPanel, position=Position(x=-6, y=0))
assembler = place_entity(
    Prototype.AssemblingMachine1,
    position=Position(x=0, y=0),
)
assembler = set_entity_recipe(assembler, Prototype.ElectronicCircuit)
assembler = insert_item(Prototype.IronPlate, assembler, 10)
assembler = insert_item(Prototype.CopperCable, assembler, 30)
print(connect_entities(solar, assembler, Prototype.SmallElectricPole))
sleep(5)
print(get_entity(Prototype.AssemblingMachine1, assembler.position))
"""
    ],
    "micro_automate_red_science_v1": [
        """\
solar = place_entity(Prototype.SolarPanel, position=Position(x=-6, y=0))
assembler = place_entity(
    Prototype.AssemblingMachine1,
    position=Position(x=0, y=0),
)
assembler = set_entity_recipe(assembler, Prototype.AutomationSciencePack)
assembler = insert_item(Prototype.IronGearWheel, assembler, 10)
assembler = insert_item(Prototype.CopperPlate, assembler, 10)
print(connect_entities(solar, assembler, Prototype.SmallElectricPole))
sleep(8)
print(get_entity(Prototype.AssemblingMachine1, assembler.position))
"""
    ],
    "micro_configure_chemical_plant_v1": [
        """\
plant = place_entity(Prototype.ChemicalPlant, position=Position(x=0, y=0))
plant = set_entity_recipe(plant, Prototype.PlasticBar)
print(plant)
"""
    ],
    "micro_configure_oil_refinery_v1": [
        """\
refinery = place_entity(Prototype.OilRefinery, position=Position(x=0, y=0))
refinery = set_entity_recipe(refinery, RecipeName.AdvancedOilProcessing)
print(refinery)
"""
    ],
    "micro_install_speed_module_v1": [
        """\
assembler = place_entity(
    Prototype.AssemblingMachine2,
    position=Position(x=0, y=0),
)
assembler = set_entity_recipe(assembler, Prototype.IronGearWheel)
assembler = insert_item(Prototype.SpeedModule, assembler, 1)
print(assembler)
"""
    ],
    "micro_place_pumpjack_v1": [
        """\
oil = nearest(Resource.CrudeOil)
move_to(oil)
pumpjack = place_entity(Prototype.PumpJack, position=oil)
print(pumpjack)
"""
    ],
    "micro_research_logistics_v1": [
        """\
solar1 = place_entity(Prototype.SolarPanel, position=Position(x=-7, y=-2))
solar2 = place_entity(Prototype.SolarPanel, position=Position(x=-7, y=2))
lab = place_entity(Prototype.Lab, position=Position(x=0, y=0))
lab = insert_item(Prototype.AutomationSciencePack, lab, 50)
print(connect_entities(solar1, lab, Prototype.SmallElectricPole))
print(set_research(Technology.Logistics))
for _ in range(45):
    sleep(15)
print(get_research_progress(Technology.Logistics))
"""
    ],
    "micro_configure_centrifuge_v1": [
        """\
centrifuge = place_entity(Prototype.Centrifuge, position=Position(x=0, y=0))
centrifuge = set_entity_recipe(centrifuge, RecipeName.UraniumProcessing)
print(centrifuge)
"""
    ],
    "micro_place_roboport_v1": [
        """\
solar1 = place_entity(Prototype.SolarPanel, position=Position(x=-8, y=-4))
solar2 = place_entity(Prototype.SolarPanel, position=Position(x=-8, y=0))
solar3 = place_entity(Prototype.SolarPanel, position=Position(x=-8, y=4))
solar4 = place_entity(Prototype.SolarPanel, position=Position(x=-4, y=-4))
roboport = place_entity(Prototype.Roboport, position=Position(x=1, y=0))
print(connect_entities(solar1, roboport, Prototype.SmallElectricPole))
sleep(3)
print(get_entity(Prototype.Roboport, roboport.position))
"""
    ],
    "micro_place_rocket_silo_v1": [
        """\
placed = None
for x in range(-20, 21, 5):
    for y in range(-20, 21, 5):
        candidate = Position(x=x, y=y)
        if can_place_entity(Prototype.RocketSilo, position=candidate):
            move_to(Position(x=x + 6, y=y))
            placed = place_entity(Prototype.RocketSilo, position=candidate)
            break
    if placed is not None:
        break
print(placed)
"""
    ],
}


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


async def run(args: argparse.Namespace) -> BenchmarkRun:
    tasks = [
        task
        for task in benchmark_catalog()
        if task.suite == "api_microtasks_v1" and task.status == "ready"
    ]
    missing = {task.task_id for task in tasks} - PROGRAMS.keys()
    if missing:
        raise RuntimeError(f"missing Codex programs: {sorted(missing)}")

    started_at = datetime.now(timezone.utc)
    observed_attempt_windows: list[tuple[datetime, datetime]] = []
    attempts: list[BenchmarkAttempt] = []
    trajectory_dir = args.output.parent / f"{args.output.stem}-trajectories"

    async with HTTPEnvironmentClient(args.envd_url, args.timeout) as client:
        for task in tasks:
            trajectory_path = trajectory_dir / f"{task.task_id}-attempt-0.json"
            if trajectory_path.exists():
                trajectory = json.loads(trajectory_path.read_text(encoding="utf-8"))
                verification = VerificationSnapshot.model_validate(
                    trajectory["verification"]
                )
                elapsed = float(trajectory["elapsed_seconds"])
                finished_at = datetime.fromisoformat(trajectory["run_at"])
                observed_attempt_windows.append(
                    (finished_at - timedelta(seconds=elapsed), finished_at)
                )
                events = verification.action_events
                attempts.append(
                    BenchmarkAttempt(
                        task_id=task.task_id,
                        task_fingerprint=task.task_spec.fingerprint,
                        attempt=0,
                        seed=task.task_spec.seed,
                        success=verification.success,
                        scalar_reward=verification.scalar_reward,
                        interventions=len(events),
                        invalid_interventions=sum(event.error for event in events),
                        retry_interventions=sum(
                            event.evaluation_retry for event in events
                        ),
                        elapsed_seconds=elapsed,
                        termination_reason=verification.termination_reason,
                        trajectory_artifact=str(
                            trajectory_path.relative_to(args.output.parent)
                        ).replace("\\", "/"),
                        metrics={
                            str(key): float(value)
                            for key, value in verification.metrics.items()
                            if isinstance(value, (int, float))
                        },
                    )
                )
                print(
                    json.dumps(
                        {
                            "task_id": task.task_id,
                            "success": verification.success,
                            "resumed_from_artifact": True,
                        }
                    ),
                    flush=True,
                )
                continue

            attempt_started = time.perf_counter()
            lease = await client.lease(task.task_spec)
            initial = await client.observe(lease.lease_id)
            actions = []
            post_observations = []
            try:
                for code in PROGRAMS[task.task_id]:
                    try:
                        result = await client.execute(lease.lease_id, code)
                    except EnvironmentClientError as exc:
                        actions.append(
                            {
                                "code": code,
                                "error": f"{type(exc).__name__}: {exc}",
                            }
                        )
                        post_observations.append(
                            (await client.observe(lease.lease_id)).model_dump(
                                mode="json"
                            )
                        )
                        break
                    actions.append(
                        {
                            "code": code,
                            "result": result.model_dump(mode="json"),
                        }
                    )
                    post_observations.append(
                        (await client.observe(lease.lease_id)).model_dump(mode="json")
                    )
                    if result.terminal_reason is not None:
                        break
                verification = await client.finalize(lease.lease_id)
            finally:
                await client.release(lease.lease_id)

            elapsed = time.perf_counter() - attempt_started
            trajectory = {
                "mode": "codex_developer_baseline",
                "model": "gpt-5.6-sol",
                "provider": "openai-codex/manual-tools",
                "non_blind": True,
                "run_at": datetime.now(timezone.utc).isoformat(),
                "task_prompt": render_task_prompt(task.task_spec),
                "task": task.task_spec.model_dump(mode="json"),
                "initial_observation": initial.model_dump(mode="json"),
                "actions": actions,
                "post_action_observations": post_observations,
                "verification": verification.model_dump(mode="json"),
                "elapsed_seconds": elapsed,
            }
            finished_at = datetime.fromisoformat(trajectory["run_at"])
            observed_attempt_windows.append(
                (finished_at - timedelta(seconds=elapsed), finished_at)
            )
            _write_json(trajectory_path, trajectory)

            events = verification.action_events
            attempts.append(
                BenchmarkAttempt(
                    task_id=task.task_id,
                    task_fingerprint=task.task_spec.fingerprint,
                    attempt=0,
                    seed=task.task_spec.seed,
                    success=verification.success,
                    scalar_reward=verification.scalar_reward,
                    interventions=len(events),
                    invalid_interventions=sum(event.error for event in events),
                    retry_interventions=sum(event.evaluation_retry for event in events),
                    elapsed_seconds=elapsed,
                    termination_reason=verification.termination_reason,
                    trajectory_artifact=str(
                        trajectory_path.relative_to(args.output.parent)
                    ).replace("\\", "/"),
                    metrics={
                        str(key): float(value)
                        for key, value in verification.metrics.items()
                        if isinstance(value, (int, float))
                    },
                )
            )
            print(
                json.dumps(
                    {
                        "task_id": task.task_id,
                        "success": verification.success,
                        "reward": verification.scalar_reward,
                        "interventions": len(events),
                        "invalid": sum(event.error for event in events),
                        "elapsed_seconds": round(elapsed, 3),
                    }
                ),
                flush=True,
            )

    if observed_attempt_windows:
        started_at = min(window[0] for window in observed_attempt_windows)
        completed_at = max(window[1] for window in observed_attempt_windows)
    else:
        completed_at = datetime.now(timezone.utc)
    run_record = BenchmarkRun(
        run_id=f"gpt-5.6-sol-developer-{started_at.strftime('%Y%m%dT%H%M%SZ')}",
        model=ModelIdentity(
            name="gpt-5.6-sol",
            provider="openai-codex/manual-tools",
            revision="Codex desktop 2026-07-27",
        ),
        suite="api_microtasks_v1",
        benchmark_split=None,
        started_at=started_at,
        completed_at=completed_at,
        repository_commit=_git_commit(),
        environment={
            "envd_url": args.envd_url,
            "factorio_version": ["2.0.73"],
            "action_profiles": ["fle-program-v1"],
            "runtime": "windows-local-docker-rcon",
            "non_blind": True,
        },
        generation_config={
            "policy_mode": "codex_authored_programs",
            "temperature": None,
            "tool_error_retries": 0,
            "attempts_per_task": 1,
            "student_visible_information_only_during_execution": True,
            "non_blind_repository_familiarity": True,
            "historical_note": (
                "The Logistics static-policy rejection occurred immediately before "
                "policy rejections became recorded ActionEvents. Its trajectory "
                "contains the rejected call, while this run's aggregate reports "
                "zero invalid interventions for that attempt."
            ),
        },
        attempts=attempts,
    )
    errors = validate_against_catalog(run_record)
    if errors:
        raise RuntimeError("invalid result:\n" + "\n".join(errors))
    _write_json(args.output, run_record.model_dump(mode="json"))
    _write_json(
        args.output.with_suffix(".summary.json"),
        summarize_run(run_record),
    )
    return run_record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--envd-url", default="http://127.0.0.1:8172")
    parser.add_argument("--timeout", type=float, default=1200)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark/results/gpt-5.6-sol-developer.json"),
    )
    args = parser.parse_args()
    result = asyncio.run(run(args))
    print(json.dumps(summarize_run(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
