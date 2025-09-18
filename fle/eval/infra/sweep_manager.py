"""
Sweep management for large-scale evaluations with multiple configurations.
"""

import asyncio
import json
import multiprocessing
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
import itertools
import random
from datetime import datetime

from fle.env.gym_env.config import GymRunConfig
from fle.commons.db_client import get_next_version
from fle.eval.analysis.database_analyzer import DatabaseAnalyzer
from fle.eval.analysis.performance_metrics import PerformanceAnalyzer
from fle.eval.analysis.wandb_logger import WandBSweepLogger
from fle.eval.infra.server_manager import get_server_manager, ServerManager
from fle.eval.tasks.task_definitions.task_registry import get_task_config


@dataclass
class SweepConfig:
    """Configuration for a large-scale evaluation sweep"""

    # Experiment metadata
    name: str
    description: str = ""

    # Model and task configurations
    models: List[str] = field(default_factory=list)
    tasks: List[str] = field(default_factory=list)  # Environment IDs
    num_trials_per_config: int = 8  # Pass@8 by default

    # Resource management
    api_keys: List[str] = field(
        default_factory=list
    )  # Deprecated - use api_key_config_file
    api_key_config_file: Optional[str] = None  # Path to JSON file with API keys
    server_configs: List[Dict[str, Any]] = field(default_factory=list)
    max_concurrent_processes: int = 4

    # Execution parameters
    shuffle_execution_order: bool = True
    retry_failed_runs: bool = True
    max_retries: int = 2

    # Pass@K optimization parameters
    task_inner_loop_mode: bool = (
        False  # Cycle through tasks before repeating model-task pairs
    )
    early_stop_on_success: bool = (
        False  # Skip (model, task) pairs that already have one success
    )

    # Logging and monitoring
    enable_wandb: bool = True
    wandb_project: str = "factorio-learning-environment"
    log_interval_minutes: int = 30  # How often to log progress summaries

    # Output configuration
    output_dir: Optional[str] = None
    save_intermediate_results: bool = True

    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.models:
            raise ValueError("At least one model must be specified")
        if not self.tasks:
            raise ValueError("At least one task must be specified")
        if self.num_trials_per_config < 1:
            raise ValueError("num_trials_per_config must be at least 1")
        if self.max_concurrent_processes < 1:
            raise ValueError("max_concurrent_processes must be at least 1")


@dataclass
class RunJob:
    """Individual run job within a sweep"""

    job_id: str
    model: str
    task: str
    trial_number: int
    sweep_id: str
    version: Optional[int] = None
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class SweepManager:
    """Manages large-scale evaluation sweeps

    Supports both new sweeps and resuming existing ones. When resuming, the manager
    will automatically skip completed runs and retry partial/failed runs.
    """

    def __init__(self, config: SweepConfig, existing_sweep_id: Optional[str] = None):
        """Initialize sweep manager

        Args:
            config: SweepConfig with sweep parameters
            existing_sweep_id: Optional sweep ID to resume an existing sweep
        """
        self.config = config
        self.is_resuming = existing_sweep_id is not None

        if existing_sweep_id:
            self.sweep_id = existing_sweep_id
            print(f"🔄 Resuming sweep: {self.sweep_id}")
        else:
            # Generate unique sweep ID with timestamp and short UUID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            short_uuid = str(uuid.uuid4())[:8]
            self.sweep_id = f"{config.name}_{timestamp}_{short_uuid}"
            print(f"🆕 Starting new sweep: {self.sweep_id}")

        self.jobs: List[RunJob] = []
        self.active_processes: Dict[str, multiprocessing.Process] = {}
        self.completed_versions: List[int] = []
        self.start_time: Optional[datetime] = None
        self.wandb_logger: Optional[WandBSweepLogger] = None
        self.database_analyzer: Optional[DatabaseAnalyzer] = None
        self.server_manager: Optional[ServerManager] = None

        if config.output_dir:
            Path(config.output_dir).mkdir(parents=True, exist_ok=True)

        # Initialize server manager
        self.server_manager = get_server_manager()
        total_servers = self.server_manager.get_total_server_count()

        # Warn if we don't have enough servers for max concurrent processes
        if total_servers < self.config.max_concurrent_processes:
            print(
                f"⚠️  Warning: Only {total_servers} Factorio servers available, "
                f"but max_concurrent_processes={self.config.max_concurrent_processes}"
            )
            print(f"   Concurrent processes will be limited to {total_servers}")
            # Adjust max concurrent processes to available servers
            self.config.max_concurrent_processes = min(
                self.config.max_concurrent_processes, total_servers
            )

        # Initialize WandB if enabled
        if config.enable_wandb:
            self.wandb_logger = WandBSweepLogger(config.wandb_project)

        # Validate configuration for early stopping
        self._validate_early_stopping_configuration()

        print(f"🆔 Sweep ID: {self.sweep_id}")
        print(
            f"🖥️  Available servers: {total_servers}, Max concurrent: {self.config.max_concurrent_processes}"
        )

        # If resuming, we'll load existing state in run_sweep()

    def _is_task_successful(self, task_name: str, reward: float) -> bool:
        """Determine if a task result is successful based on task-specific criteria

        Args:
            task_name: Name of the task (e.g., 'advanced_circuit_throughput')
            reward: Final reward achieved

        Returns:
            True if the task was successful, False otherwise
        """
        try:
            # Get task configuration to determine success criteria
            task_config = get_task_config(task_name)
            config_dict = task_config.to_dict()

            # For throughput tasks, success is meeting the quota
            if config_dict.get("task_type") == "throughput":
                quota = config_dict.get("quota", 16)  # Default quota is 16
                return reward >= quota

            # For unbounded throughput tasks, success is also meeting quota
            elif config_dict.get("task_type") == "unbounded_throughput":
                # Unbounded tasks might not have explicit quota, use 16 as default
                quota = config_dict.get("quota", 16)
                return reward >= quota

            # For other task types, use positive reward as success criteria
            else:
                return reward > 0

        except Exception as e:
            # Fallback to simple positive reward check if task config unavailable
            print(
                f"⚠️  Warning: Could not determine success criteria for task '{task_name}': {e}"
            )
            print("    Using fallback success criteria (reward > 0)")
            return reward > 0

    def _validate_early_stopping_configuration(self):
        """Validate configuration settings related to early stopping"""

        if not self.config.early_stop_on_success:
            return  # No validation needed if early stopping is disabled

        print("🎯 Early stopping enabled - validating configuration...")

        # Check if database analyzer can be initialized
        try:
            if not self.database_analyzer:
                test_analyzer = DatabaseAnalyzer()  # noqa
                # We don't keep this, just test if it can be created
                print("✅ Database analyzer can be initialized for early stopping")
        except Exception as db_init_error:
            print(
                "🚨 CRITICAL: Early stopping enabled but database analyzer cannot be initialized"
            )
            print(f"    Database initialization error: {db_init_error}")
            print(
                "    Early stopping will NOT work - consider disabling early_stop_on_success"
            )
            print("    Or fix database connection issues before running sweep")

        # Validate task inner loop mode compatibility
        if self.config.task_inner_loop_mode and self.config.shuffle_execution_order:
            print(
                "💡 Note: shuffle_execution_order is disabled when task_inner_loop_mode=True"
            )
            print(
                "    This ensures tasks are executed in the intended order for WandB visibility"
            )

        # Check if configuration makes sense
        if self.config.num_trials_per_config == 1 and self.config.early_stop_on_success:
            print("⚠️  WARNING: early_stop_on_success=True with num_trials_per_config=1")
            print(
                "    Early stopping provides no benefit with only 1 trial per (model, task) pair"
            )
            print(
                "    Consider increasing num_trials_per_config for meaningful Pass@K evaluation"
            )

        if self.config.early_stop_on_success and not self.is_resuming:
            print(
                "💡 Note: For new sweeps, early stopping will only activate after first successes"
            )
            print(
                "    Initial trials will run normally until successful (model, task) pairs are found"
            )

        # Warn about potential compute savings
        max_possible_jobs = (
            len(self.config.models)
            * len(self.config.tasks)
            * self.config.num_trials_per_config
        )
        if self.config.early_stop_on_success and max_possible_jobs > 50:
            print("💰 Early stopping could save significant compute budget:")
            print(f"    Maximum possible jobs: {max_possible_jobs}")
            print(
                f"    If each (model, task) pair succeeds early, could save ~{max_possible_jobs * 0.5:.0f}+ jobs"
            )

    @classmethod
    def resume_sweep(cls, config: SweepConfig, sweep_id: str) -> "SweepManager":
        """Create a SweepManager to resume an existing sweep

        Args:
            config: SweepConfig with sweep parameters (should match original config)
            sweep_id: ID of the existing sweep to resume

        Returns:
            SweepManager instance configured to resume the sweep
        """
        return cls(config, existing_sweep_id=sweep_id)

    async def load_existing_sweep_state(self) -> Dict[str, Any]:
        """Load existing sweep state from database

        Returns:
            Dictionary with information about completed runs
        """
        if not self.is_resuming:
            return {"completed_runs": {}, "partial_runs": {}}

        print(f"🔍 Loading existing state for sweep: {self.sweep_id}")

        # Initialize database analyzer if not already done
        if not self.database_analyzer:
            self.database_analyzer = DatabaseAnalyzer()

        try:
            # Get existing trajectories for this sweep
            try:
                existing_df = (
                    await self.database_analyzer.get_trajectory_summaries_by_sweep(
                        self.sweep_id
                    )
                )
            except Exception as db_error:
                print("🚨 CRITICAL: Failed to query database for existing sweep state")
                print(f"    Database error: {db_error}")
                print("    Sweep resumption will proceed as if no previous runs exist")
                print(
                    "    This may cause duplicate work if sweep actually has previous results"
                )
                return {"completed_runs": {}, "partial_runs": {}}

            if existing_df.empty:
                print(f"💡 No existing trajectory data found for sweep {self.sweep_id}")
                print(
                    "    This is normal for new sweeps or if previous sweep had no successful completions"
                )
                return {"completed_runs": {}, "partial_runs": {}}

            print(
                f"📊 Found {len(existing_df)} existing trajectories for sweep {self.sweep_id}"
            )

            successful_runs = {}  # key: (model, task), value: True if any success exists
            finished_runs = {}  # key: (model, task), value: count of finished runs
            partial_runs = {}  # key: (model, task, trial), value: {version, status} - only for truly incomplete runs

            # Group by version to identify complete vs partial runs
            parsing_errors = []
            task_extraction_failures = 0

            for idx, row in existing_df.iterrows():
                try:
                    model = row.get("model", "unknown_model")
                    version_desc = row.get("version_description", "")
                    version = row.get("version", -1)
                    instance = row.get("instance", 0)  # This is the trial number

                    # Validate essential fields
                    if not model or model == "unknown_model":
                        parsing_errors.append(f"Row {idx}: missing or invalid model")
                        continue
                    if version == -1:
                        parsing_errors.append(f"Row {idx}: missing or invalid version")
                        continue

                    # Extract task from version_description
                    task = "unknown_task"
                    if version_desc and "type:" in version_desc:
                        try:
                            task = version_desc.split("type:")[1].split("\n")[0].strip()
                        except (IndexError, AttributeError):
                            task_extraction_failures += 1
                            task = f"parse_failed_{version}"
                    elif version_desc:
                        # Fallback: use first line or part of version_description
                        try:
                            task = version_desc.split("\n")[0].strip()
                            if not task:
                                task = f"empty_desc_{version}"
                        except AttributeError:
                            task = f"malformed_desc_{version}"
                    else:
                        task = f"no_desc_{version}"
                        task_extraction_failures += 1

                    # Keys for tracking
                    model_task_key = (model, task)
                    run_key = (model, task, instance)

                    num_steps = row.get("num_steps", 0)
                    final_reward = row.get("final_reward", 0)

                    # Consider a run finished if it has reasonable number of steps (likely completed full trajectory)
                    # For throughput tasks, typical trajectory length is 64 steps
                    is_finished = (
                        num_steps >= 40
                    )  # Must have at least 64 steps to be considered finished

                    # Track if this (model, task) pair has any successful run
                    if self._is_task_successful(task, final_reward):
                        successful_runs[model_task_key] = True

                    if is_finished:
                        # Count all finished runs for this (model, task) pair
                        finished_runs[model_task_key] = (
                            finished_runs.get(model_task_key, 0) + 1
                        )
                    else:
                        # Only treat truly incomplete runs (< 30 steps) as partial/retry candidates
                        partial_runs[run_key] = {
                            "version": version,
                            "num_steps": num_steps,
                            "final_reward": final_reward,
                            "status": "incomplete",
                        }

                except Exception as parse_error:
                    parsing_errors.append(f"Row {idx}: {parse_error}")
                    continue

            # Report parsing issues
            if parsing_errors:
                print(
                    f"⚠️  WARNING: Found {len(parsing_errors)} trajectory data parsing errors:"
                )
                for error in parsing_errors[:5]:  # Show first 5 errors
                    print(f"    {error}")
                if len(parsing_errors) > 5:
                    print(f"    ... and {len(parsing_errors) - 5} more errors")
                print("    These trajectories will be ignored for sweep resumption")

            if task_extraction_failures > 0:
                print(
                    f"⚠️  WARNING: Failed to extract task names from {task_extraction_failures} trajectories"
                )
                print("    These may not be properly handled for early stopping")

            print(f"✅ Found {len(successful_runs)} (model, task) pairs with successes")
            print(f"📊 Found {sum(finished_runs.values())} total finished runs")
            print(f"⚠️  Found {len(partial_runs)} partial/incomplete runs")

            # Log some examples
            if successful_runs:
                print("Examples of successful (model, task) pairs:")
                for i, (model, task) in enumerate(list(successful_runs.keys())[:3]):
                    finished_count = finished_runs.get((model, task), 0)
                    print(f"  - {model} on {task} ({finished_count} finished runs)")

            if partial_runs:
                print("Examples of partial runs (will be retried):")
                for i, (model, task, trial) in enumerate(list(partial_runs.keys())[:3]):
                    info = partial_runs[(model, task, trial)]
                    print(
                        f"  - {model} on {task} trial {trial} ({info['num_steps']} steps)"
                    )

            return {
                "successful_runs": successful_runs,
                "finished_runs": finished_runs,
                "partial_runs": partial_runs,
                "total_existing": len(existing_df),
            }

        except Exception as e:
            print(f"❌ Error loading existing sweep state: {e}")
            return {"successful_runs": {}, "finished_runs": {}, "partial_runs": {}}

    def generate_jobs(
        self, existing_state: Optional[Dict[str, Any]] = None
    ) -> List[RunJob]:
        """Generate all run jobs for the sweep using the corrected criteria:
        - For each (model, task) pair: if successful -> launch 0 jobs, else launch (8 - num_finished) jobs

        Args:
            existing_state: Optional dictionary with successful runs, finished runs, and partial run information

        Returns:
            List of RunJob objects to execute
        """
        jobs = []
        successful_runs = (
            existing_state.get("successful_runs", {}) if existing_state else {}
        )
        finished_runs = (
            existing_state.get("finished_runs", {}) if existing_state else {}
        )
        partial_runs = existing_state.get("partial_runs", {}) if existing_state else {}

        skipped_count = 0
        retry_count = 0
        early_stop_count = 0

        # For early stopping, we use the successful_runs directly
        if self.config.early_stop_on_success:
            if not successful_runs:
                if self.is_resuming:
                    print(
                        "💡 Early stopping enabled but no successful (model, task) pairs found"
                    )
                    print("    Will launch jobs according to (8 - num_finished) rule")
                else:
                    print(
                        "💡 Early stopping enabled for new sweep - no previous successes to check"
                    )
            else:
                print(
                    f"🎯 Early stopping enabled: Found {len(successful_runs)} successful (model, task) pairs"
                )
                print("    These pairs will have 0 new jobs launched")

        # Generate jobs based on the new rule: for each (model, task) pair:
        # - If successful -> launch 0 jobs
        # - Else -> launch (num_trials_per_config - num_finished) jobs

        # First add partial runs that need retry
        for (model, task, trial), info in partial_runs.items():
            job_id = f"{model}_{task}_trial{trial:02d}"
            job = RunJob(
                job_id=job_id,
                model=model,
                task=task,
                trial_number=trial,
                sweep_id=self.sweep_id,
            )
            job.retry_count = 1
            job.status = "pending"
            jobs.append(job)
            retry_count += 1
            print(f"🔄 Will retry partial run: {job_id}")

        # Now generate new jobs based on (model, task) pair logic
        for model, task in itertools.product(self.config.models, self.config.tasks):
            model_task_key = (model, task)

            # If this (model, task) pair already succeeded and early stopping is enabled, skip it
            if self.config.early_stop_on_success and model_task_key in successful_runs:
                early_stop_count += self.config.num_trials_per_config
                print(
                    f"⏩ Early stopping: {model} + {task} already successful - skipping all trials"
                )
                continue

            # Calculate how many finished runs we have for this (model, task) pair
            num_finished = finished_runs.get(model_task_key, 0)

            # Calculate how many new jobs we need: max(0, num_trials_per_config - num_finished)
            # We don't count partial runs since they'll be retried separately
            num_new_jobs = max(0, self.config.num_trials_per_config - num_finished)

            # Always log the calculation for debugging
            print(
                f"📊 {model} + {task}: {num_finished} finished out of {self.config.num_trials_per_config}, launching {num_new_jobs} new jobs"
            )

            # Skip if we don't need any new jobs
            if num_new_jobs == 0:
                skipped_count += self.config.num_trials_per_config
                continue

            # Generate the needed new jobs, using trial numbers starting from num_finished
            for trial_offset in range(num_new_jobs):
                trial = num_finished + trial_offset

                # Make sure we don't exceed the configured number of trials
                if trial >= self.config.num_trials_per_config:
                    break

                job_id = f"{model}_{task}_trial{trial:02d}"
                job = RunJob(
                    job_id=job_id,
                    model=model,
                    task=task,
                    trial_number=trial,
                    sweep_id=self.sweep_id,
                )
                jobs.append(job)

        # Shuffle only if not using task inner loop mode and shuffle is enabled
        if self.config.shuffle_execution_order and not self.config.task_inner_loop_mode:
            random.shuffle(jobs)

        self.jobs = jobs

        # Log summary
        total_expected = (
            len(self.config.models)
            * len(self.config.tasks)
            * self.config.num_trials_per_config
        )
        total_finished = sum(finished_runs.values())

        print("📋 Job generation summary:")
        print(f"   Total possible jobs: {total_expected}")
        print(f"   Already finished: {total_finished}")
        print(f"   Will retry (partial): {retry_count}")
        if self.config.early_stop_on_success:
            print(f"   Early stopped (successful pairs): {early_stop_count}")
        print(f"   New jobs to run: {len(jobs) - retry_count}")
        print(f"   Total jobs to execute: {len(jobs)}")

        # Log execution mode
        if self.config.early_stop_on_success:
            print(
                "⏩ Early stopping enabled: Rule = if successful -> 0 jobs, else -> (8 - num_finished) jobs"
            )

        return jobs

    async def run_sweep(self) -> Dict[str, Any]:
        """Execute the complete sweep

        Returns:
            Dictionary with sweep results and statistics
        """
        print(f"Starting sweep: {self.config.name}")
        print(
            f"Total configurations: {len(self.config.models)} models × {len(self.config.tasks)} tasks × {self.config.num_trials_per_config} trials = {len(self.config.models) * len(self.config.tasks) * self.config.num_trials_per_config} runs"
        )

        self.start_time = datetime.now()

        # Load existing state if resuming
        existing_state = await self.load_existing_sweep_state()

        # Generate all jobs (excluding completed ones if resuming)
        self.generate_jobs(existing_state)

        # Initialize database analyzer for monitoring (if not already initialized)
        if not self.database_analyzer:
            self.database_analyzer = DatabaseAnalyzer()

        # Get starting version numbers
        base_version = await get_next_version()

        # Assign version numbers to jobs
        for i, job in enumerate(self.jobs):
            job.version = base_version + i

        try:
            # Main execution loop
            await self.execute_jobs()

            # Final analysis and reporting
            results = await self.generate_final_report()

            print(
                f"Sweep completed successfully! Total time: {datetime.now() - self.start_time}"
            )
            return results

        finally:
            # Cleanup
            if self.database_analyzer:
                await self.database_analyzer.cleanup()
            if self.wandb_logger:
                self.wandb_logger.finish_all()

    async def execute_jobs(self):
        """Execute all jobs with concurrency management"""

        def get_pending_jobs():
            return [job for job in self.jobs if job.status == "pending"]

        pending_jobs = get_pending_jobs()

        while pending_jobs or self.active_processes:
            # Refresh pending jobs list to account for early stopping
            pending_jobs = get_pending_jobs()

            # Start new processes if slots are available
            while (
                len(self.active_processes) < self.config.max_concurrent_processes
                and pending_jobs
            ):
                job = pending_jobs.pop(0)
                await self.start_job(job)

            # Check for completed processes
            completed_job_ids = []
            for job_id, process in self.active_processes.items():
                if not process.is_alive():
                    completed_job_ids.append(job_id)

            # Handle completed jobs
            for job_id in completed_job_ids:
                await self.handle_completed_job(job_id)

            # Log progress periodically
            await self.log_progress_if_needed()

            # Brief sleep to avoid busy waiting
            await asyncio.sleep(1)

        print("All jobs completed!")

    async def start_job(self, job: RunJob):
        """Start execution of a single job

        Args:
            job: RunJob to execute
        """
        print(f"Starting job: {job.job_id} (version {job.version})")

        # Allocate a server for this job
        server_allocation = self.server_manager.allocate_server(job.job_id)
        if not server_allocation:
            job.status = "failed"
            job.error_message = "No Factorio servers available"
            job.end_time = datetime.now()
            print(f"❌ Failed to start job {job.job_id}: No servers available")
            return

        print(
            f"🖥️  Allocated server {server_allocation.server_id} "
            f"({server_allocation.server_address}:{server_allocation.tcp_port}) "
            f"to job {job.job_id}"
        )

        # Create run configuration
        run_config = GymRunConfig(env_id=job.task, model=job.model, version=job.version)

        # Create gym eval config (similar to run_eval.py)
        try:
            job.status = "running"
            job.start_time = datetime.now()

            # Start the process
            process = multiprocessing.Process(
                target=self.run_job_wrapper,
                args=(
                    job.job_id,
                    run_config,
                    job.version,
                    job.sweep_id,
                    server_allocation,
                    self.config.api_key_config_file,
                ),
            )
            process.start()
            server_allocation.process_id = process.pid
            self.active_processes[job.job_id] = process

            # Log to WandB if enabled
            if self.wandb_logger:
                logger = self.wandb_logger.create_run_logger(
                    job.job_id,
                    job.model,
                    job.task,
                    job.version,
                    config={
                        "sweep_id": self.sweep_id,
                        "is_resume": self.is_resuming,
                        "retry_count": job.retry_count,
                        "trial_number": job.trial_number,
                    },
                    tags=[f"sweep:{self.sweep_id}"],
                )
                logger.log_metrics(
                    {
                        "job/status": "started",
                        "job/server_id": server_allocation.server_id,
                        "job/server_address": server_allocation.server_address,
                        "job/server_port": server_allocation.tcp_port,
                        "job/sweep_id": self.sweep_id,
                        "job/is_resume": self.is_resuming,
                        "job/retry_count": job.retry_count,
                        "job/completion_status": "running",
                    }
                )

        except Exception as e:
            # Release server if process failed to start
            self.server_manager.release_server(job.job_id)
            job.status = "failed"
            job.error_message = str(e)
            job.end_time = datetime.now()
            print(f"❌ Failed to start job {job.job_id}: {e}")

    @staticmethod
    def run_job_wrapper(
        job_id: str,
        run_config: GymRunConfig,
        version: int,
        sweep_id: str,
        server_allocation,  # ServerAllocation object
        api_key_config_file: Optional[str] = None,
    ):
        """Wrapper for running a job in a subprocess

        Args:
            job_id: Unique job identifier
            run_config: GymRunConfig for this job
            version: Version number for this job
            sweep_id: Unique identifier for this sweep
            server_allocation: ServerAllocation object with server details
            api_key_config_file: Optional path to API key config file
        """
        try:
            # Set environment variables
            if api_key_config_file:
                os.environ["FLE_API_KEY_CONFIG_FILE"] = api_key_config_file

            # Set sweep ID environment variable for database and WandB logging
            os.environ["FLE_SWEEP_ID"] = sweep_id

            # Set server allocation environment variables
            os.environ["FACTORIO_SERVER_ADDRESS"] = server_allocation.server_address
            os.environ["FACTORIO_SERVER_PORT"] = str(server_allocation.tcp_port)
            os.environ["FLE_SERVER_ID"] = str(server_allocation.server_id)

            # Override PORT_OFFSET to ensure we use the allocated server
            os.environ["PORT_OFFSET"] = str(server_allocation.server_id)

            # This would be similar to the run_process function in run_eval.py
            # but adapted for single configurations
            print(
                f"Executing job {job_id} with version {version} (sweep: {sweep_id}) "
                f"on server {server_allocation.server_id} ({server_allocation.server_address}:{server_allocation.tcp_port})"
            )

            # Create a temporary config file for this job
            config_data = [run_config.__dict__]

            # Run the evaluation (this would call the actual evaluation logic)
            asyncio.run(SweepManager._execute_single_evaluation(config_data, job_id))

            print(f"Job {job_id} completed successfully")

        except Exception as e:
            print(f"Job {job_id} failed: {e}")
            raise

    @staticmethod
    async def _execute_single_evaluation(config_data: List[Dict], job_id: str):
        """Execute a single evaluation run

        Args:
            config_data: List with single run config
            job_id: Job identifier for logging
        """
        # Import here to avoid circular imports
        from fle.env.gym_env.run_eval import main as run_eval_main

        # Create temporary config file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            temp_config_path = f.name

        try:
            # Run evaluation with the temporary config
            await run_eval_main(temp_config_path)
        finally:
            # Clean up temporary file
            Path(temp_config_path).unlink(missing_ok=True)

    async def handle_completed_job(self, job_id: str):
        """Handle a completed job

        Args:
            job_id: ID of the completed job
        """
        process = self.active_processes.pop(job_id)
        job = next(job for job in self.jobs if job.job_id == job_id)

        job.end_time = datetime.now()

        # Release the server allocated to this job
        server_released = self.server_manager.release_server(job_id)
        if server_released:
            print(f"🔓 Released server for completed job {job_id}")
        else:
            print(f"⚠️  No server allocation found for job {job_id}")

        if process.exitcode == 0:
            job.status = "completed"
            self.completed_versions.append(job.version)
            print(f"✅ Job {job_id} completed successfully")

            # Check for dynamic early stopping if enabled
            if self.config.early_stop_on_success:
                await self.check_dynamic_early_stopping(job)

            # Log completion to WandB
            if self.wandb_logger:
                logger = self.wandb_logger.get_logger(job_id)
                if logger:
                    logger.log_metrics(
                        {
                            "job/status": "completed",
                            "job/completion_status": "successful",
                            "job/exit_code": process.exitcode,
                            "job/duration_minutes": (
                                job.end_time - job.start_time
                            ).total_seconds()
                            / 60
                            if job.start_time
                            else 0,
                            "job/final_retry_count": job.retry_count,
                        }
                    )

        else:
            job.status = "failed"
            job.error_message = f"Process exited with code {process.exitcode}"
            print(f"❌ Job {job_id} failed with exit code {process.exitcode}")

            # Log failure to WandB
            if self.wandb_logger:
                logger = self.wandb_logger.get_logger(job_id)
                if logger:
                    will_retry = (
                        self.config.retry_failed_runs
                        and job.retry_count < self.config.max_retries
                    )
                    logger.log_metrics(
                        {
                            "job/status": "failed",
                            "job/completion_status": "will_retry"
                            if will_retry
                            else "failed_final",
                            "job/exit_code": process.exitcode,
                            "job/error_message": job.error_message,
                            "job/duration_minutes": (
                                job.end_time - job.start_time
                            ).total_seconds()
                            / 60
                            if job.start_time
                            else 0,
                            "job/retry_count_at_failure": job.retry_count,
                        }
                    )

            # Retry if configured and retries available
            if (
                self.config.retry_failed_runs
                and job.retry_count < self.config.max_retries
            ):
                print(
                    f"🔄 Retrying job {job_id} (attempt {job.retry_count + 1}/{self.config.max_retries})"
                )
                job.retry_count += 1
                job.status = "pending"
                job.start_time = None
                job.end_time = None
                job.error_message = None
                # Note: Server will be reallocated when job is retried

    async def check_dynamic_early_stopping(self, completed_job: RunJob):
        """Check if we can early stop more jobs based on a newly completed successful job

        Args:
            completed_job: The job that just completed successfully
        """
        try:
            # Check if this job was successful by querying the database
            if not self.database_analyzer:
                print(
                    f"🚨 CRITICAL: Dynamic early stopping failed for job {completed_job.job_id} - database analyzer unavailable"
                )
                print(
                    "    Early stopping will not work until database connection is restored"
                )
                return

            # Get the result for this specific job
            try:
                job_results = await self.database_analyzer.get_trajectory_summaries(
                    [completed_job.version]
                )
            except Exception as db_error:
                print(
                    f"🚨 CRITICAL: Database query failed for job {completed_job.job_id} early stopping check"
                )
                print(f"    Database error: {db_error}")
                print("    This job's success cannot be determined for early stopping")
                return

            if job_results.empty:
                print(
                    f"⚠️  WARNING: No trajectory data found for completed job {completed_job.job_id} (version {completed_job.version})"
                )
                print(
                    "    This could mean: database write lag, transaction not committed, or data corruption"
                )
                print(
                    "    Early stopping cannot proceed for this job - other jobs may continue unnecessarily"
                )
                return

            # Check if it was successful using task-specific criteria
            try:
                final_reward = job_results.iloc[0].get("final_reward", 0)
                if final_reward is None:
                    print(
                        f"⚠️  WARNING: Job {completed_job.job_id} has null final_reward - cannot determine success"
                    )
                    print("    Assuming job failed for early stopping purposes")
                    return

                # Use task-specific success criteria
                if not self._is_task_successful(completed_job.task, final_reward):
                    print(
                        f"💡 Job {completed_job.job_id} completed but was not successful (reward: {final_reward}) - no early stopping needed"
                    )
                    return
            except (KeyError, IndexError, TypeError) as parse_error:
                print(
                    f"⚠️  WARNING: Could not parse success status for job {completed_job.job_id}"
                )
                print(f"    Parse error: {parse_error}")
                print(
                    "    Raw job data structure may be malformed - early stopping skipped for this job"
                )
                return

            print(f"🎯 Job {completed_job.job_id} succeeded with reward {final_reward}")

            # Cancel pending jobs for the same (model, task) pair
            model_task_pair = (completed_job.model, completed_job.task)
            cancelled_count = 0

            for job in self.jobs:
                if (
                    job.status == "pending"
                    and job.model == completed_job.model
                    and job.task == completed_job.task
                    and job.job_id != completed_job.job_id
                ):
                    job.status = "early_stopped"
                    job.end_time = datetime.now()
                    cancelled_count += 1
                    print(
                        f"⏩ Early stopping job {job.job_id} - {model_task_pair} already successful"
                    )

            if cancelled_count > 0:
                print(
                    f"🎯 Early stopped {cancelled_count} jobs for successful {model_task_pair}"
                )
            else:
                print(
                    f"💡 No pending jobs found to early stop for successful {model_task_pair}"
                )

        except Exception as e:
            print(
                f"🚨 CRITICAL: Unexpected error in dynamic early stopping check for job {completed_job.job_id}"
            )
            print(f"    Error: {e}")
            print(
                "    Early stopping functionality may be compromised - consider disabling early_stop_on_success"
            )
            import traceback

            print(f"    Stack trace: {traceback.format_exc()}")

    async def log_progress_if_needed(self):
        """Log progress summary if enough time has elapsed"""
        if not hasattr(self, "_last_progress_log"):
            self._last_progress_log = time.time()
            return

        elapsed_minutes = (time.time() - self._last_progress_log) / 60

        if elapsed_minutes >= self.config.log_interval_minutes:
            await self.log_progress_summary()
            self._last_progress_log = time.time()

    async def log_progress_summary(self):
        """Log current progress summary"""
        total_jobs = len(self.jobs)
        completed = len([j for j in self.jobs if j.status == "completed"])
        running = len([j for j in self.jobs if j.status == "running"])
        failed = len([j for j in self.jobs if j.status == "failed"])
        early_stopped = len([j for j in self.jobs if j.status == "early_stopped"])
        pending = total_jobs - completed - running - failed - early_stopped

        elapsed_time = datetime.now() - self.start_time

        # Get server allocation status
        server_status = self.server_manager.get_allocation_status()

        print("\n=== Sweep Progress ===")
        print(f"Total jobs: {total_jobs}")
        print(f"Completed: {completed} ({completed / total_jobs * 100:.1f}%)")
        print(f"Running: {running}")
        print(f"Failed: {failed}")
        if early_stopped > 0:
            print(f"Early stopped: {early_stopped}")
        print(f"Pending: {pending}")
        print(f"Elapsed time: {elapsed_time}")

        print("\n🖥️  Server Status:")
        print(f"Total servers: {server_status['total_servers']}")
        print(f"Available: {server_status['available_servers']}")
        print(f"Allocated: {server_status['allocated_servers']}")

        if completed > 0:
            avg_time_per_job = elapsed_time.total_seconds() / completed
            eta_seconds = avg_time_per_job * pending
            eta_hours = eta_seconds / 3600
            print(f"\n⏱️  ETA: {eta_hours:.1f} hours")

        # Analyze recent results if we have completed jobs
        if self.completed_versions and self.database_analyzer:
            try:
                await self.analyze_recent_results()
            except Exception as e:
                print(f"Error analyzing recent results: {e}")

        print("=" * 22 + "\n")

    async def analyze_recent_results(self):
        """Analyze results from recently completed jobs"""
        if not self.database_analyzer or not self.completed_versions:
            return

        try:
            # Get recent results
            recent_results = await self.database_analyzer.get_trajectory_summaries(
                self.completed_versions[-20:]  # Last 20 completed
            )

            if recent_results.empty:
                return

            # Group by model for quick analysis
            model_success_rates = {}
            for model in recent_results["model"].unique():
                model_data = recent_results[recent_results["model"] == model]

                # Count successes using task-specific criteria
                success_count = 0
                for _, row in model_data.iterrows():
                    task_name = "unknown_task"
                    version_desc = row.get("version_description", "")
                    if version_desc and "type:" in version_desc:
                        try:
                            task_name = (
                                version_desc.split("type:")[1].split("\n")[0].strip()
                            )
                        except (IndexError, AttributeError):
                            pass

                    final_reward = row.get("final_reward", 0)
                    if self._is_task_successful(task_name, final_reward):
                        success_count += 1

                total_count = len(model_data)
                success_rate = success_count / total_count if total_count > 0 else 0
                model_success_rates[model] = {
                    "success_rate": success_rate,
                    "completed_trajectories": total_count,
                }

            print("Recent results by model:")
            for model, stats in model_success_rates.items():
                print(
                    f"  {model}: {stats['success_rate']:.1%} success ({stats['completed_trajectories']} trajectories)"
                )

            # Log to WandB if enabled
            if self.wandb_logger:
                for model, stats in model_success_rates.items():
                    # Create a temporary logger for sweep-level metrics
                    temp_logger = self.wandb_logger.create_run_logger(
                        f"sweep_progress_{model}",
                        model,
                        "sweep_summary",
                        0,
                        config={"type": "progress_summary"},
                    )
                    temp_logger.log_metrics(
                        {
                            "progress/success_rate": stats["success_rate"],
                            "progress/completed_trajectories": stats[
                                "completed_trajectories"
                            ],
                        }
                    )

        except Exception as e:
            print(f"Error in recent results analysis: {e}")

    async def generate_final_report(self) -> Dict[str, Any]:
        """Generate final sweep report with comprehensive analysis

        Returns:
            Dictionary containing sweep results and analysis
        """
        print("\nGenerating final sweep report...")

        if not self.database_analyzer:
            return {"error": "Database analyzer not available"}

        try:
            # Get all results from the sweep
            all_versions = [job.version for job in self.jobs if job.version]
            results_df = await self.database_analyzer.get_trajectory_summaries(
                all_versions
            )

            if results_df.empty:
                return {"error": "No results found"}

            # Calculate performance metrics by model and task
            results_by_model = {}
            results_by_task = {}

            for model in results_df["model"].unique():
                model_data = results_df[results_df["model"] == model]
                metrics = PerformanceAnalyzer.calculate_metrics(
                    model_data,
                    reward_column="final_reward",
                    token_column="total_tokens",
                    step_column="num_steps",
                )
                # Add production score metrics if available
                if "max_production_score" in model_data.columns:
                    production_metrics = PerformanceAnalyzer.calculate_metrics(
                        model_data,
                        reward_column="max_production_score",
                        token_column="total_tokens",
                        step_column="num_steps",
                    )
                    # Store production score metrics in the metrics object
                    metrics.production_score_mean = production_metrics.mean_reward
                    metrics.production_score_max = production_metrics.max_reward
                    metrics.production_score_std = production_metrics.std_reward

                results_by_model[model] = metrics

            for task_desc in results_df["version_description"].unique():
                task_data = results_df[results_df["version_description"] == task_desc]
                # Extract task name from version description
                task_name = (
                    task_desc.split("type:")[1].split("\n")[0]
                    if "type:" in task_desc
                    else task_desc
                )
                metrics = PerformanceAnalyzer.calculate_metrics(
                    task_data,
                    reward_column="final_reward",
                    token_column="total_tokens",
                    step_column="num_steps",
                )
                # Add production score metrics if available
                if "max_production_score" in task_data.columns:
                    production_metrics = PerformanceAnalyzer.calculate_metrics(
                        task_data,
                        reward_column="max_production_score",
                        token_column="total_tokens",
                        step_column="num_steps",
                    )
                    # Store production score metrics in the metrics object
                    metrics.production_score_mean = production_metrics.mean_reward
                    metrics.production_score_max = production_metrics.max_reward
                    metrics.production_score_std = production_metrics.std_reward

                results_by_task[task_name] = metrics

            # Calculate overall statistics
            total_trajectories = len(results_df)
            total_time = (datetime.now() - self.start_time).total_seconds()

            # Generate comprehensive report
            report = {
                "sweep_id": self.sweep_id,
                "sweep_config": self.config.__dict__,
                "execution_summary": {
                    "total_jobs": len(self.jobs),
                    "completed_jobs": len(
                        [j for j in self.jobs if j.status == "completed"]
                    ),
                    "failed_jobs": len([j for j in self.jobs if j.status == "failed"]),
                    "early_stopped_jobs": len(
                        [j for j in self.jobs if j.status == "early_stopped"]
                    ),
                    "total_trajectories": total_trajectories,
                    "total_time_hours": total_time / 3600,
                    "avg_time_per_trajectory": total_time / max(total_trajectories, 1),
                    "task_inner_loop_mode": self.config.task_inner_loop_mode,
                    "early_stop_on_success": self.config.early_stop_on_success,
                },
                "results_by_model": {
                    model: metrics.to_dict()
                    for model, metrics in results_by_model.items()
                },
                "results_by_task": {
                    task: metrics.to_dict() for task, metrics in results_by_task.items()
                },
                "timestamp": datetime.now().isoformat(),
            }

            # Log comprehensive results to WandB
            if self.wandb_logger:
                # Create a final summary logger
                summary_logger = self.wandb_logger.create_run_logger(
                    "sweep_final_summary",
                    "all_models",
                    "final_summary",
                    0,
                    config={
                        **report["sweep_config"],
                        "sweep_id": self.sweep_id,
                        "is_resume": self.is_resuming,
                        "sweep_completion_status": "completed",
                    },
                    tags=[f"sweep:{self.sweep_id}", "sweep_summary"],
                )

                summary_logger.log_sweep_summary(
                    self.config.__dict__,
                    results_by_model,
                    results_by_task,
                    total_trajectories,
                    total_time,
                )

                # Log model comparison table
                summary_logger.log_model_comparison_table(results_by_model)

                # Log sweep completion metrics
                summary_logger.log_metrics(
                    {
                        "sweep/completion_status": "completed",
                        "sweep/is_resume": self.is_resuming,
                        "sweep/total_completed_jobs": report["execution_summary"][
                            "completed_jobs"
                        ],
                        "sweep/total_failed_jobs": report["execution_summary"][
                            "failed_jobs"
                        ],
                        "sweep/success_rate": report["execution_summary"][
                            "completed_jobs"
                        ]
                        / max(report["execution_summary"]["total_jobs"], 1),
                        "sweep/final_timestamp": datetime.now().timestamp(),
                    }
                )

            # Save report to file if output directory specified
            if self.config.output_dir:
                report_path = (
                    Path(self.config.output_dir)
                    / f"sweep_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                )
                with open(report_path, "w") as f:
                    json.dump(report, f, indent=2, default=str)
                print(f"Report saved to: {report_path}")

            return report

        except Exception as e:
            print(f"Error generating final report: {e}")
            return {"error": str(e)}

    def get_status_summary(self) -> Dict[str, Any]:
        """Get current status summary of the sweep

        Returns:
            Dictionary with current status information
        """
        total = len(self.jobs)
        completed = len([j for j in self.jobs if j.status == "completed"])
        running = len([j for j in self.jobs if j.status == "running"])
        failed = len([j for j in self.jobs if j.status == "failed"])
        early_stopped = len([j for j in self.jobs if j.status == "early_stopped"])
        pending = total - completed - running - failed - early_stopped

        return {
            "total_jobs": total,
            "completed": completed,
            "running": running,
            "failed": failed,
            "early_stopped": early_stopped,
            "pending": pending,
            "completion_rate": completed / total if total > 0 else 0,
            "active_processes": len(self.active_processes),
            "elapsed_time": (datetime.now() - self.start_time)
            if self.start_time
            else None,
        }
