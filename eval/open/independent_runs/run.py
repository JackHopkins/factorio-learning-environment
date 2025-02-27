import asyncio
import argparse
import multiprocessing
from dotenv import load_dotenv
from agents.basic_agent import BasicAgent
from eval.open.independent_runs.trajectory_runner import run_process, get_next_version, create_factorio_instance, construct_task_object, EvalConfig
from eval.tasks.throughput_task import ThroughputTask
from pathlib import Path
load_dotenv()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume-versions', type=str, help='Comma-separated list of versions to resume from')
    args = parser.parse_args()
    task_folder = Path("eval", "tasks", "task_definitions") 
    # Create initial state and get system prompt
    instance = create_factorio_instance(0)
    system_prompt = instance.get_system_prompt()

    plastic_bar_task = construct_task_object(task_folder, "plastic_bar_throughput_16", instance, ThroughputTask)
    steel_plate_task = construct_task_object(task_folder, "steel_plate_throughput_16", instance, ThroughputTask)
    electronic_circuit_task = construct_task_object(task_folder, "electronic_circuit_throughput_16", instance, ThroughputTask)
    lubricant_task = construct_task_object(task_folder, "lubricant_throughput_16", instance, ThroughputTask)
    light_oil_task = construct_task_object(task_folder, "light_oil_throughput_16", instance, ThroughputTask)
    sulfur_task = construct_task_object(task_folder, "sulfur_throughput_16", instance, ThroughputTask)
    petro_task = construct_task_object(task_folder, "petroleum_gas_throughput_16", instance, ThroughputTask)
    steel_plate_task = construct_task_object(task_folder, "steel_plate_throughput_16", instance, ThroughputTask)
    electronic_circuit_task = construct_task_object(task_folder, "electronic_circuit_throughput_16", instance, ThroughputTask)
    red_science_task = construct_task_object(task_folder, "automation_science_pack_throughput_16", instance, ThroughputTask)
    gear_wheel_task = construct_task_object(task_folder, "iron_gear_wheel_throughput_16", instance, ThroughputTask)
    
    run_configs = [
        {"agent": BasicAgent(model="gpt-4o-mini-2024-07-18", system_prompt=system_prompt, goal = red_science_task.goal_description), "resume_version": 887, "task": red_science_task},
        {"agent": BasicAgent(model="gpt-4o-mini-2024-07-18", system_prompt=system_prompt, goal = red_science_task.goal_description), "resume_version": 888, "task": red_science_task},
        {"agent": BasicAgent(model="gpt-4o-mini-2024-07-18", system_prompt=system_prompt, goal = red_science_task.goal_description), "resume_version": 889, "task": red_science_task},
        {"agent": BasicAgent(model="gpt-4o-mini-2024-07-18", system_prompt=system_prompt, goal = red_science_task.goal_description), "resume_version": 890, "task": red_science_task},
        {"agent": BasicAgent(model="gpt-4o-mini-2024-07-18", system_prompt=system_prompt, goal = steel_plate_task.goal_description), "resume_version": 891, "task": steel_plate_task},
        {"agent": BasicAgent(model="gpt-4o-mini-2024-07-18", system_prompt=system_prompt, goal = steel_plate_task.goal_description), "resume_version": 892, "task": steel_plate_task},
        {"agent": BasicAgent(model="gpt-4o-mini-2024-07-18", system_prompt=system_prompt, goal = steel_plate_task.goal_description), "resume_version": 893, "task": steel_plate_task},
        {"agent": BasicAgent(model="gpt-4o-mini-2024-07-18", system_prompt=system_prompt, goal = steel_plate_task.goal_description), "resume_version": 894, "task": steel_plate_task},
        {"agent": BasicAgent(model="gpt-4o-mini-2024-07-18", system_prompt=system_prompt, goal = lubricant_task.goal_description), "resume_version": 895, "task": lubricant_task},
        {"agent": BasicAgent(model="gpt-4o-mini-2024-07-18", system_prompt=system_prompt, goal = lubricant_task.goal_description), "resume_version": 896, "task": lubricant_task},
        {"agent": BasicAgent(model="gpt-4o-mini-2024-07-18", system_prompt=system_prompt, goal = lubricant_task.goal_description), "resume_version": 897, "task": lubricant_task},
        {"agent": BasicAgent(model="gpt-4o-mini-2024-07-18", system_prompt=system_prompt, goal = lubricant_task.goal_description), "resume_version": 898, "task": lubricant_task},
    ]

    # Update resume versions if provided
    #if args.resume_versions:
    #    versions = [int(v.strip()) if v.strip() else None for v in args.resume_versions.split(',')]
    #    for i, version in enumerate(versions[:len(run_configs)]):
    #        if version is not None:
    #            run_configs[i]["resume_version"] = version


    # Get starting version number for new runs
    base_version = asyncio.run(get_next_version())

    processes = []
    for run_idx, run_config in enumerate(run_configs):
        config = EvalConfig(
            agent=run_config["agent"],
            version=run_config["resume_version"] if run_config["resume_version"] else base_version + run_idx,
            version_description=f"model:{run_config['agent'].model}\ntype:{run_config['task'].task_key}",
            resume_version=run_config["resume_version"],
            task=run_config["task"]
        )

        p = multiprocessing.Process(
            target=run_process,
            args=(run_idx, config)
        )
        p.start()
        processes.append(p)

    # Wait for all processes to complete
    for p in processes:
        p.join()


if __name__ == "__main__":
    multiprocessing.set_start_method('spawn')
    main()