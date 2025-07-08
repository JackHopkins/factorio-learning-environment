import multiprocessing
import os
import time
from typing import Optional

from fle.agents.gym_agent import GymAgent
from fle.commons.models.program import Program

from fle.env.gym_env.observation import Observation


class TrajectoryLogger:
    """Handles logging for trajectory runs with persistent state"""

    def __init__(
        self, start_time: float, trajectory_length: int, log_dir: Optional[str] = None
    ):
        """Initialize the trajectory logger

        Args:
            start_time: Start time of the trajectory
            trajectory_length: Total length of the trajectory
            log_dir: Directory to save log files
        """
        self.start_time = start_time
        self.trajectory_length = trajectory_length
        self.log_dir = log_dir
        self.iteration_times = []
        if log_dir is not None:
            os.makedirs(log_dir, exist_ok=True)

    def get_eta(self, current_iteration: int) -> str:
        """Calculate estimated time remaining

        Args:
            current_iteration: Current iteration number

        Returns:
            Formatted ETA string as HH:MM:SS
        """
        if not self.iteration_times:
            return "calculating..."

        # Keep only the last 50 iteration times for more accurate recent average
        recent_times = self.iteration_times[-50:]
        avg_iteration_time = sum(recent_times) / len(recent_times)
        remaining_iterations = self.trajectory_length - current_iteration
        seconds_remaining = avg_iteration_time * remaining_iterations

        # Convert to hours:minutes:seconds
        hours = int(seconds_remaining // 3600)
        minutes = int((seconds_remaining % 3600) // 60)
        seconds = int(seconds_remaining % 60)

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def log_progress(self, agent: GymAgent, iteration: int, program_value: float):
        """Log progress of the trajectory run

        Args:
            agent: The agent instance
            iteration: Current iteration number
            program_value: Value of the current program
        """
        elapsed = time.time() - self.start_time
        elapsed_str = f"{int(elapsed // 3600):02d}:{int((elapsed % 3600) // 60):02d}:{int(elapsed % 60):02d}"
        eta = self.get_eta(iteration)
        print(
            f"\033[92m Process {multiprocessing.current_process().name} - "
            f"Model: {agent.model} - "
            f"Iteration {iteration}/{self.trajectory_length} - "
            f"Value: {program_value:.2f} - "
            f"Elapsed: {elapsed_str} - "
            f"ETA: {eta}\033[0m"
        )

    def log_observation_and_program(
        self,
        agent: GymAgent,
        agent_idx: int,
        iteration: int,
        observation: Observation,
        program: Program,
    ):
        """Log observation and program to console and files

        Args:
            agent: The agent instance
            agent_idx: Index of the agent
            iteration: Current iteration number
            observation: The observation to log
            program: The program to log
        """
        # Log program
        print(
            f"\n\033[95mProgram for agent {agent_idx} at iteration {iteration}:\033[0m"
        )
        print(program.code)

        if self.log_dir:
            prog_file = os.path.join(
                self.log_dir, f"agent{agent_idx}_iter{iteration}_program.py"
            )
            with open(prog_file, "w") as f:
                f.write(program.code)

        # Log observation
        formatted_obs = agent.observation_formatter.format(observation).raw_str
        print(
            f"\n\033[94mObservation for agent {agent_idx} at iteration {iteration}:\033[0m"
        )
        print(formatted_obs)

        if self.log_dir:
            obs_file = os.path.join(
                self.log_dir, f"agent{agent_idx}_iter{iteration}_observation.txt"
            )
            with open(obs_file, "w") as f:
                f.write(formatted_obs)

    def add_iteration_time(self, iteration_time: float):
        """Add an iteration time to the tracking list

        Args:
            iteration_time: Time taken for the iteration
        """
        self.iteration_times.append(iteration_time)
