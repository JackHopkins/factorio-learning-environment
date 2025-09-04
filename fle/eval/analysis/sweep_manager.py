"""
Sweep management for large-scale evaluations with multiple configurations.
"""

import asyncio
import json
import multiprocessing
import os
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path
import itertools
import random
from datetime import datetime

from fle.env.gym_env.config import GymRunConfig
from fle.commons.db_client import get_next_version
from .database_analyzer import DatabaseAnalyzer
from .performance_metrics import PerformanceAnalyzer
from .wandb_logger import WandBSweepLogger


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
    version: Optional[int] = None
    status: str = "pending"  # pending, running, completed, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0


class SweepManager:
    """Manages large-scale evaluation sweeps"""

    def __init__(self, config: SweepConfig):
        """Initialize sweep manager

        Args:
            config: SweepConfig with sweep parameters
        """
        self.config = config
        self.jobs: List[RunJob] = []
        self.active_processes: Dict[str, multiprocessing.Process] = {}
        self.completed_versions: List[int] = []
        self.start_time: Optional[datetime] = None
        self.wandb_logger: Optional[WandBSweepLogger] = None
        self.database_analyzer: Optional[DatabaseAnalyzer] = None

        if config.output_dir:
            Path(config.output_dir).mkdir(parents=True, exist_ok=True)

        # Initialize WandB if enabled
        if config.enable_wandb:
            self.wandb_logger = WandBSweepLogger(config.wandb_project)

    def generate_jobs(self) -> List[RunJob]:
        """Generate all run jobs for the sweep

        Returns:
            List of RunJob objects
        """
        jobs = []

        # Generate all combinations of models and tasks
        for model, task in itertools.product(self.config.models, self.config.tasks):
            for trial in range(self.config.num_trials_per_config):
                job_id = f"{model}_{task}_trial{trial:02d}"
                job = RunJob(job_id=job_id, model=model, task=task, trial_number=trial)
                jobs.append(job)

        # Shuffle if requested to distribute load
        if self.config.shuffle_execution_order:
            random.shuffle(jobs)

        self.jobs = jobs
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

        # Generate all jobs
        self.generate_jobs()

        # Initialize database analyzer for monitoring
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
        pending_jobs = [job for job in self.jobs if job.status == "pending"]

        while pending_jobs or self.active_processes:
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
                    self.config.api_key_config_file,
                ),
            )
            process.start()
            self.active_processes[job.job_id] = process

            # Log to WandB if enabled
            if self.wandb_logger:
                logger = self.wandb_logger.create_run_logger(
                    job.job_id, job.model, job.task, job.version
                )
                logger.log_metrics({"job/status": "started"})

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.end_time = datetime.now()
            print(f"Failed to start job {job.job_id}: {e}")

    @staticmethod
    def run_job_wrapper(
        job_id: str,
        run_config: GymRunConfig,
        version: int,
        api_key_config_file: Optional[str] = None,
    ):
        """Wrapper for running a job in a subprocess

        Args:
            job_id: Unique job identifier
            run_config: GymRunConfig for this job
            version: Version number for this job
            api_key_config_file: Optional path to API key config file
        """
        try:
            # Set environment variable for API key config if provided
            if api_key_config_file:
                os.environ["FLE_API_KEY_CONFIG_FILE"] = api_key_config_file

            # This would be similar to the run_process function in run_eval.py
            # but adapted for single configurations
            print(f"Executing job {job_id} with version {version}")

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

        if process.exitcode == 0:
            job.status = "completed"
            self.completed_versions.append(job.version)
            print(f"Job {job_id} completed successfully")

            # Log completion to WandB
            if self.wandb_logger:
                logger = self.wandb_logger.get_logger(job_id)
                if logger:
                    logger.log_metrics({"job/status": "completed"})

        else:
            job.status = "failed"
            job.error_message = f"Process exited with code {process.exitcode}"
            print(f"Job {job_id} failed with exit code {process.exitcode}")

            # Retry if configured and retries available
            if (
                self.config.retry_failed_runs
                and job.retry_count < self.config.max_retries
            ):
                print(
                    f"Retrying job {job_id} (attempt {job.retry_count + 1}/{self.config.max_retries})"
                )
                job.retry_count += 1
                job.status = "pending"
                job.start_time = None
                job.end_time = None
                job.error_message = None

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
        pending = total_jobs - completed - running - failed

        elapsed_time = datetime.now() - self.start_time

        print("\n=== Sweep Progress ===")
        print(f"Total jobs: {total_jobs}")
        print(f"Completed: {completed} ({completed / total_jobs * 100:.1f}%)")
        print(f"Running: {running}")
        print(f"Failed: {failed}")
        print(f"Pending: {pending}")
        print(f"Elapsed time: {elapsed_time}")

        if completed > 0:
            avg_time_per_job = elapsed_time.total_seconds() / completed
            eta_seconds = avg_time_per_job * pending
            eta_hours = eta_seconds / 3600
            print(f"ETA: {eta_hours:.1f} hours")

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
                success_count = len(model_data[model_data["final_reward"] > 0])
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
                results_by_task[task_name] = metrics

            # Calculate overall statistics
            total_trajectories = len(results_df)
            total_time = (datetime.now() - self.start_time).total_seconds()

            # Generate comprehensive report
            report = {
                "sweep_config": self.config.__dict__,
                "execution_summary": {
                    "total_jobs": len(self.jobs),
                    "completed_jobs": len(
                        [j for j in self.jobs if j.status == "completed"]
                    ),
                    "failed_jobs": len([j for j in self.jobs if j.status == "failed"]),
                    "total_trajectories": total_trajectories,
                    "total_time_hours": total_time / 3600,
                    "avg_time_per_trajectory": total_time / max(total_trajectories, 1),
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
                    config=report["sweep_config"],
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
        pending = total - completed - running - failed

        return {
            "total_jobs": total,
            "completed": completed,
            "running": running,
            "failed": failed,
            "pending": pending,
            "completion_rate": completed / total if total > 0 else 0,
            "active_processes": len(self.active_processes),
            "elapsed_time": (datetime.now() - self.start_time)
            if self.start_time
            else None,
        }
