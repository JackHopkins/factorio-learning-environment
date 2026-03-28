#!/usr/bin/env python3
"""Export FLE throughput tasks to Harbor-compatible format.

This script converts FLE's throughput tasks into the directory structure
expected by Harbor for vendor evaluation.

Usage:
    python export_tasks_for_harbor.py

Output:
    vendor_eval_tasks/
      <task_name>/
        environment/Dockerfile
        task.toml
        tests/test_task.py
"""

import sys
import shutil
from pathlib import Path

# Add project root to path to import FLE modules
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import THROUGHPUT_TASKS


def copy_factorio_config(task_dir: Path):
    """Copy Factorio server config files to task directory.

    Args:
        task_dir: Task directory to copy config files to
    """
    source_config = project_root / "fle" / "cluster" / "config"
    dest_config = task_dir / "environment" / "config"
    dest_config.mkdir(parents=True, exist_ok=True)

    config_files = [
        "server-settings.json",
        "map-gen-settings.json",
        "map-settings.json",
        "config.ini",
        "rconpw",
        "server-adminlist.json",
    ]

    for filename in config_files:
        source_file = source_config / filename
        if source_file.exists():
            shutil.copy(source_file, dest_config / filename)


def copy_factorio_scenarios(task_dir: Path):
    """Copy Factorio scenarios to task directory.

    Args:
        task_dir: Task directory to copy scenarios to
    """
    source_scenarios = project_root / "fle" / "cluster" / "scenarios"
    dest_scenarios = task_dir / "environment" / "scenarios"

    if dest_scenarios.exists():
        shutil.rmtree(dest_scenarios)

    shutil.copytree(source_scenarios, dest_scenarios)


def create_supervisord_conf(task_dir: Path):
    """Create supervisord.conf for managing Factorio server and task runner.

    Args:
        task_dir: Task directory to create supervisor config in
    """
    supervisord_conf = """[supervisord]
nodaemon=true
logfile=/dev/stdout
logfile_maxbytes=0
loglevel=info

[program:factorio]
command=/opt/factorio/bin/x64/factorio \
    --start-server-load-scenario default_lab_scenario \
    --port 34197 \
    --rcon-port 27000 \
    --rcon-password factorio \
    --server-settings /opt/factorio/config/server-settings.json \
    --map-gen-settings /opt/factorio/config/map-gen-settings.json \
    --map-settings /opt/factorio/config/map-settings.json
autostart=true
autorestart=false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
priority=1
startsecs=10

[program:task_runner]
command=/usr/bin/python3 /workspace/task_runner.py
autostart=true
autorestart=false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
priority=2
startsecs=0
# Start after factorio (priority 2 > priority 1)
startretries=3
"""
    (task_dir / "environment" / "supervisord.conf").write_text(supervisord_conf)


def create_entrypoint_script(task_dir: Path, task_key: str):
    """Create entrypoint.sh script that Harbor will execute.

    Args:
        task_dir: Task directory to create entrypoint in
        task_key: Task identifier
    """
    entrypoint_sh = f"""#!/bin/bash
set -e

# This script is executed by Harbor to run the task
# Harbor mounts task.toml at /task/task.toml

echo "=========================================="
echo "FLE Harbor Task Entrypoint"
echo "Task: {task_key}"
echo "=========================================="

# Copy task.toml to workspace (Harbor mounts it at /task/)
if [ -f /task/task.toml ]; then
    cp /task/task.toml /workspace/task.toml
    echo "✓ Copied task.toml"
else
    echo "⚠ Warning: task.toml not found at /task/task.toml"
fi

# Start supervisor (which will start Factorio and then task_runner)
echo "Starting supervisor..."
exec /usr/bin/supervisord -c /etc/supervisord.conf
"""
    entrypoint_path = task_dir / "environment" / "entrypoint.sh"
    entrypoint_path.write_text(entrypoint_sh)
    entrypoint_path.chmod(0o755)


def create_task_runner(task_dir: Path, task_key: str):
    """Create task_runner.py script that bridges Harbor and FLE.

    Args:
        task_dir: Task directory to create task runner in
        task_key: Task identifier
    """
    task_runner_py = '''#!/usr/bin/env python3
"""Harbor task runner for FLE evaluation.

This script:
1. Waits for Factorio server to be ready
2. Reads Harbor configuration
3. Runs Inspect AI evaluation
4. Exports results to Harbor format
"""

import os
import sys
import time
import json
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def wait_for_factorio_server(host="localhost", port=27000, password="factorio", timeout=120):
    """Wait for Factorio server to be ready by polling RCON.

    Args:
        host: RCON host
        port: RCON port
        password: RCON password
        timeout: Maximum wait time in seconds

    Returns:
        True if server is ready, False if timeout
    """
    logger.info(f"Waiting for Factorio server at {host}:{port}...")

    # Import RCON client (included with FLE dependencies)
    from factorio_rcon import RCONClient

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            client = RCONClient(host, port, password)
            response = client.send_command('/c game.print("ready")')
            client.close()
            logger.info(f"✓ Factorio server ready after {time.time() - start_time:.1f}s")
            return True
        except Exception as e:
            logger.debug(f"Server not ready yet: {e}")
            time.sleep(2)

    logger.error(f"Timeout waiting for Factorio server after {timeout}s")
    return False


def run_evaluation():
    """Run Inspect AI evaluation and export to Harbor format."""

    # Read Harbor environment variables
    task_id = os.getenv("HARBOR_TASK_ID", "unknown")
    run_id = os.getenv("HARBOR_RUN_ID", "0")
    output_dir = Path(os.getenv("HARBOR_OUTPUT_DIR", "/workspace/output"))
    model = os.getenv("HARBOR_MODEL", "openrouter/anthropic/claude-opus-4-6")

    # Read task.toml
    import tomli

    task_toml_path = Path("/workspace/task.toml")
    if not task_toml_path.exists():
        logger.error(f"task.toml not found at {task_toml_path}")
        return False

    with open(task_toml_path, "rb") as f:
        config = tomli.load(f)

    env_id = config["task"]["name"]
    quota = config["scoring"]["quota"]
    trajectory_length = config["scoring"]["trajectory_length"]

    logger.info(f"Task: {env_id}")
    logger.info(f"Model: {model}")
    logger.info(f"Quota: {quota}")
    logger.info(f"Trajectory length: {trajectory_length}")
    logger.info(f"Output directory: {output_dir}")

    # Ensure output directory and inspect_logs subdirectory exist
    output_dir.mkdir(parents=True, exist_ok=True)
    inspect_logs_dir = output_dir / "inspect_logs"
    inspect_logs_dir.mkdir(parents=True, exist_ok=True)

    # Run Inspect AI evaluation
    try:
        from inspect_ai import eval as inspect_eval
        from fle.eval.inspect_integration.vendor_eval_throughput import create_vendor_eval_task

        logger.info("Creating vendor eval task...")
        task = create_vendor_eval_task([env_id], k=1, name=f"{env_id}_harbor")

        logger.info(f"Running evaluation with model {model}...")
        result = inspect_eval(
            task,
            model=model,
            log_dir=str(inspect_logs_dir),
            sandbox=None  # Disable sandbox - we're already in a container
        )

        logger.info("✓ Evaluation complete")

        # Export to Harbor format
        from fle.eval.inspect_integration.vendor_eval_adapter import export_inspect_results

        logger.info("Exporting results to Harbor format...")
        trial_dirs = export_inspect_results(
            eval_log_dir=str(output_dir / "inspect_logs"),
            output_dir=str(output_dir),
            task_names=[env_id]
        )

        if trial_dirs:
            logger.info(f"✓ Results exported to {len(trial_dirs)} trial directories")

            # Verify result.json exists
            result_json = output_dir / "result.json"
            if result_json.exists():
                logger.info(f"✓ result.json created at {result_json}")
                with open(result_json) as f:
                    result_data = json.load(f)
                    logger.info(f"  Score: {result_data.get('score', 'N/A')}")
            else:
                logger.warning("result.json not found")

            # Verify trajectory.json exists
            traj_json = output_dir / "agent" / "trajectory.json"
            if traj_json.exists():
                logger.info(f"✓ trajectory.json created at {traj_json}")
            else:
                logger.warning("trajectory.json not found")

            return True
        else:
            logger.error("No trial directories generated")
            return False

    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("FLE Harbor Task Runner")
    logger.info("=" * 60)

    # Step 1: Wait for Factorio server
    if not wait_for_factorio_server():
        logger.error("Failed to connect to Factorio server")
        # Signal supervisor to stop Factorio
        os.system("supervisorctl stop factorio")
        sys.exit(1)

    # Step 2: Run evaluation
    success = run_evaluation()

    # Step 3: Stop Factorio server
    logger.info("Stopping Factorio server...")
    os.system("supervisorctl stop factorio")

    # Step 4: Exit with appropriate status code
    if success:
        logger.info("✅ Task completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Task failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
    (task_dir / "environment" / "task_runner.py").write_text(task_runner_py)
    (task_dir / "environment" / "task_runner.py").chmod(0o755)


def export_task_for_harbor(task_key: str, output_dir: Path):
    """Export a single task to Harbor format.

    Args:
        task_key: Task identifier (e.g., 'iron_ore_throughput')
        output_dir: Base directory for task export
    """
    task_config = THROUGHPUT_TASKS[task_key]
    task_dir = output_dir / task_key
    task_dir.mkdir(parents=True, exist_ok=True)

    # Get entity string (handle Prototype enum if needed)
    entity = task_config.throughput_entity
    if hasattr(entity, "value"):
        entity = entity.value
        if isinstance(entity, tuple):
            entity = entity[0]

    # Create task.toml with Harbor-expected format
    task_toml = f"""# Harbor task configuration for {task_key}

[task]
name = "{task_key}"
description = "{task_config.goal_description}"
timeout = 3600  # 1 hour timeout per task

[scoring]
type = "throughput"
quota = {task_config.quota}
entity = "{entity}"
trajectory_length = {task_config.trajectory_length}
holdout_wait_period = {task_config.holdout_wait_period}
pre_holdout_wait_period = {task_config.pre_holdout_wait_period}

[environment]
type = "factorio"
"""

    (task_dir / "task.toml").write_text(task_toml)

    # Create environment/Dockerfile
    env_dir = task_dir / "environment"
    env_dir.mkdir(exist_ok=True)

    # Get current FLE version from pyproject.toml if possible
    dockerfile = f"""# Factorio Learning Environment for Harbor evaluation
# This container runs both a Factorio server and the FLE evaluation agent
FROM factoriotools/factorio:2.0.73

# Switch to root to install dependencies
USER root

# Install Python and system dependencies (Debian-based)
RUN apt-get update && apt-get install -y \\
    python3 \\
    python3-pip \\
    python3-dev \\
    python3-setuptools \\
    build-essential \\
    supervisor \\
    git \\
    && rm -rf /var/lib/apt/lists/*

# Install Python packages (using --break-system-packages for containerized env)
# Note: factorio-rcon-py is included as a dependency of FLE
# Using --ignore-installed to avoid conflicts with Debian packages
# Add cache-busting argument to force git refetch on updates
ARG CACHEBUST=1
RUN pip3 install --no-cache-dir --break-system-packages --ignore-installed \\
    git+https://github.com/JackHopkins/PaperclipMaximiser.git@harbor-integration \\
    inspect-ai \\
    tomli \\
    fastapi \\
    uvicorn

# Copy Factorio configuration files
COPY config/* /opt/factorio/config/

# Copy Factorio scenarios
COPY scenarios /opt/factorio/scenarios

# Copy task runner and entrypoint
COPY task_runner.py /workspace/task_runner.py
COPY entrypoint.sh /workspace/entrypoint.sh

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisord.conf

# Set up environment variables
ENV FACTORIO_ENV_ID={task_key}
ENV FLE_TRAJECTORY_LENGTH={task_config.trajectory_length}
ENV FACTORIO_SERVER_ADDRESS=localhost
ENV FACTORIO_SERVER_PORT=27000
ENV PYTHONUNBUFFERED=1
ENV FLE_VISION=false

# Create output directory
RUN mkdir -p /workspace/output

WORKDIR /opt/fle_task

# Entry point: Harbor will call this
ENTRYPOINT ["/workspace/entrypoint.sh"]
"""

    (env_dir / "Dockerfile").write_text(dockerfile)

    # Copy Factorio configuration files
    copy_factorio_config(task_dir)

    # Copy Factorio scenarios
    copy_factorio_scenarios(task_dir)

    # Create supervisor configuration
    create_supervisord_conf(task_dir)

    # Create task runner script
    create_task_runner(task_dir, task_key)

    # Create entrypoint script
    create_entrypoint_script(task_dir, task_key)

    # Create tests directory with verification script
    tests_dir = task_dir / "tests"
    tests_dir.mkdir(exist_ok=True)

    test_py = f"""#!/usr/bin/env python3
\"\"\"Verification test for {task_key}.

This script verifies that the task configuration is valid and
provides basic information about the task.

Note: This does NOT start a Factorio server - it only validates the config.
\"\"\"
import sys
from pathlib import Path

try:
    from fle.eval.tasks.task_definitions.lab_play.throughput_tasks import THROUGHPUT_TASKS
    from fle.eval.tasks import TaskFactory

    def verify_task():
        \"\"\"Verify task configuration and print info.\"\"\"
        task_config = THROUGHPUT_TASKS["{task_key}"]

        print("=" * 60)
        print(f"Task: {{task_config.task_key}}")
        print("=" * 60)
        print(f"Goal: {{task_config.goal_description}}")
        print(f"Quota: {{task_config.quota}} per 60 seconds")
        print(f"Entity: {{task_config.throughput_entity}}")
        print(f"Trajectory length: {{task_config.trajectory_length}} steps")
        print(f"Holdout wait period: {{task_config.holdout_wait_period}} seconds")
        print()

        # Verify task can be created via TaskFactory
        print("Verifying task can be loaded...")
        task = TaskFactory.create_task("{task_key}")

        print("✓ Task configuration valid")
        print(f"Task type: {{task.__class__.__name__}}")
        print(f"Task key: {{task.task_key}}")
        print()
        print("✅ Task verification passed!")
        print()
        print("Note: To run this task with Harbor:")
        print(f"  harbor run -p vendor_eval_tasks \\\\")
        print(f"    -m openrouter/anthropic/claude-opus-4-6 \\\\")
        print(f"    -a terminus-2 -k 1")

        return True

    if __name__ == "__main__":
        success = verify_task()
        sys.exit(0 if success else 1)

except ImportError as e:
    print(f"Error: FLE not installed - {{e}}")
    print("Install with: pip install factorio-learning-environment")
    sys.exit(1)
except Exception as e:
    print(f"Error during verification: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
"""

    (tests_dir / "test_task.py").write_text(test_py)
    (tests_dir / "test_task.py").chmod(0o755)

    # Create README
    readme = f"""# {task_key}

{task_config.goal_description}

## Task Details

- **Quota:** {task_config.quota} items per 60 seconds
- **Entity:** {entity}
- **Trajectory Length:** {task_config.trajectory_length} steps
- **Task Type:** Throughput

## Running with Harbor

```bash
harbor run \\
  -p . \\
  -m openrouter/anthropic/claude-opus-4-6 \\
  -a terminus-2 \\
  -k 8 \\
  --job-name {task_key}-eval \\
  --jobs-dir eval_results
```

## Verification

Run the verification test:

```bash
python tests/test_task.py
```

## Scoring

The task is scored based on throughput proportion:
- **Reward = min(achieved / quota, 1.0)**
- Full score (1.0) requires producing {task_config.quota} items/minute
- Partial credit given for lower throughput
"""

    (task_dir / "README.md").write_text(readme)

    print(f"✓ Exported {task_key}")


def main():
    """Export tasks for vendor evaluation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Export FLE tasks to Harbor-compatible format"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("vendor_eval_tasks"),
        help="Output directory for task export (default: vendor_eval_tasks)",
    )
    parser.add_argument(
        "--config",
        choices=["k8", "k4", "k2", "full", "custom"],
        default="k8",
        help="Task configuration to export (default: k8)",
    )
    parser.add_argument(
        "--tasks",
        nargs="+",
        help="Custom task list (only with --config custom)",
    )

    args = parser.parse_args()

    # Select tasks based on configuration
    if args.config == "k8":
        # 4 tasks × 8 rollouts = 32 samples
        selected_tasks = [
            "iron_ore_throughput",
            "electronic_circuit_throughput",
            "plastic_bar_throughput",
            "logistics_science_pack_throughput",
        ]
        print("Configuration: vendor_eval_32_k8 (4 tasks × 8 rollouts)")

    elif args.config == "k4":
        # 8 tasks × 4 rollouts = 32 samples
        selected_tasks = [
            "iron_ore_throughput",
            "iron_plate_throughput",
            "electronic_circuit_throughput",
            "steel_plate_throughput",
            "crude_oil_throughput",
            "plastic_bar_throughput",
            "advanced_circuit_throughput",
            "logistics_science_pack_throughput",
        ]
        print("Configuration: vendor_eval_32_k4 (8 tasks × 4 rollouts)")

    elif args.config == "k2":
        # 16 tasks × 2 rollouts = 32 samples
        selected_tasks = [
            "iron_ore_throughput",
            "iron_plate_throughput",
            "iron_gear_wheel_throughput",
            "inserter_throughput",
            "electronic_circuit_throughput",
            "automation_science_pack_throughput",
            "steel_plate_throughput",
            "plastic_bar_throughput",
            "crude_oil_throughput",
            "petroleum_gas_throughput",
            "sulfur_throughput",
            "sufuric_acid_throughput",
            "advanced_circuit_throughput",
            "battery_throughput",
            "processing_unit_throughput",
            "logistics_science_pack_throughput",
        ]
        print("Configuration: vendor_eval_32 (16 tasks × 2 rollouts)")

    elif args.config == "full":
        # All tasks × 1 rollout
        selected_tasks = list(THROUGHPUT_TASKS.keys())
        print(
            f"Configuration: vendor_eval_full (all {len(selected_tasks)} tasks × 1 rollout)"
        )

    elif args.config == "custom":
        if not args.tasks:
            print("Error: --tasks required with --config custom")
            sys.exit(1)
        selected_tasks = args.tasks
        print(f"Configuration: custom ({len(selected_tasks)} tasks)")

    # Create output directory
    output_dir = args.output_dir
    output_dir.mkdir(exist_ok=True)

    # Export each task
    print(f"\nExporting {len(selected_tasks)} tasks to {output_dir}/\n")
    for task_key in selected_tasks:
        if task_key not in THROUGHPUT_TASKS:
            print(f"⚠ Warning: Unknown task '{task_key}', skipping")
            continue
        export_task_for_harbor(task_key, output_dir)

    # Create index README
    index_readme = f"""# Vendor Eval Tasks for Harbor

This directory contains {len(selected_tasks)} Factorio throughput tasks exported for
Harbor evaluation and vendor-eval-kit collection.

## Configuration: {args.config}

## Tasks

"""
    for i, task_key in enumerate(selected_tasks, 1):
        if task_key in THROUGHPUT_TASKS:
            task_config = THROUGHPUT_TASKS[task_key]
            index_readme += f"{i}. **{task_key}**: {task_config.goal_description}\\n"

    index_readme += f"""
## Directory Structure

Each task directory contains:
- `environment/Dockerfile` - Docker environment setup
- `task.toml` - Task configuration for Harbor
- `tests/test_task.py` - Verification script
- `README.md` - Task documentation

## Running Evaluation

```bash
# Test single task first
harbor run \\
  -p {output_dir} \\
  -m openrouter/anthropic/claude-opus-4-6 \\
  -a terminus-2 \\
  -k 1 \\
  --job-name test-run \\
  --jobs-dir eval_results_test

# Full evaluation with all 3 models
harbor run \\
  -p {output_dir} \\
  -m openrouter/anthropic/claude-opus-4-6 \\
  -m openrouter/openai/gpt-5.3-codex \\
  -m openrouter/x-ai/grok-4.20-beta \\
  -a terminus-2 \\
  -k 8 \\
  --job-name vendor-eval \\
  --jobs-dir eval_results

# Collect results
vendor-eval collect eval_results -o eval_csvs/
```

## Verification

Test individual tasks:

```bash
cd {output_dir}/iron_ore_throughput
python tests/test_task.py
```

## Generated

- Export script: `export_tasks_for_harbor.py`
- Configuration: `{args.config}`
- Date: {__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

    (output_dir / "README.md").write_text(index_readme)

    print(f"\n✓ Successfully exported {len(selected_tasks)} tasks to {output_dir}/")
    print("\nTask structure:")
    print(f"  {output_dir}/")
    for task_key in selected_tasks[:3]:  # Show first 3 as examples
        print(f"    {task_key}/")
        print("      environment/Dockerfile")
        print("      task.toml")
        print("      tests/test_task.py")
        print("      README.md")
    if len(selected_tasks) > 3:
        print(f"    ... and {len(selected_tasks) - 3} more tasks")

    print("\n📋 Next steps:")
    print(
        f"  1. Test single task: cd {output_dir} && harbor run -p . -m openrouter/anthropic/claude-opus-4-6 -a terminus-2 -k 1"
    )
    print("  2. Review VENDOR_EVAL_HARBOR_SETUP.md for full guide")
    print("  3. Run full evaluation with k=8 across all 3 models")


if __name__ == "__main__":
    main()
